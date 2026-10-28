"""Rebuild UTF-8 CSV outputs from explicit assumptions; standard library only."""
import csv
import json
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with (ROOT / 'assumptions.csv').open(encoding='utf-8-sig', newline='') as f:
    INPUT = {r['key']: D(r['value']) for r in csv.DictReader(f)}

CATEGORIES = ['Оборудование CapEx', 'Лицензии и подписки OpEx', 'ФОТ поддержки',
              'Выезды и командировки', 'Каналы связи', 'Электроэнергия серверов',
              'Ремонт оборудования', 'Облачная платформа и backup', 'ИИ и контроль качества',
              'Интеграция POS HAL ERP', 'Разработка SKU matching', 'Миграция магазинов',
              'Обучение', 'Резерв рисков миграции']

def write_csv(name, header, rows):
    with (ROOT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def amounts(a, stores):
    return {
        'Оборудование CapEx': stores * a['legacy_refresh_share'] * a['legacy_server_price'] / 12,
        'Лицензии и подписки OpEx': stores * a['legacy_license'],
        'ФОТ поддержки': stores * a['legacy_support'],
        'Выезды и командировки': stores * a['legacy_visits'],
        'Каналы связи': stores * a['legacy_network'],
        'Электроэнергия серверов': stores * a['legacy_power'],
        'Ремонт оборудования': stores * a['legacy_repairs'],
    }

def model(overrides=None):
    a = INPUT | (overrides or {})
    n = int(a['stores'])
    months = int(a['months'])
    assert n == 100 and months == 36, 'Rollout is specified for 100 stores and 36 months'
    assert a['overlap_months'] == 1, 'This model implements one overlap month per store'
    rollout = [10, 15, 20, 20, 20, 15] + [0] * 30
    assert sum(rollout) == n
    active = 0
    rows = []
    transition_total = D(0)
    for m, added in enumerate(rollout, 1):
        # All new stores incur target costs this month; their legacy costs end next month.
        legacy = n - active
        active += added
        old = {k: D(0) for k in CATEGORIES} | amounts(a, D(n))
        new = {k: D(0) for k in CATEGORIES} | amounts(a, D(legacy))
        new['Лицензии и подписки OpEx'] += active * (a['pos_saas'] + a['hal_fleet'])
        new['ФОТ поддержки'] += active * a['target_support']
        new['Выезды и командировки'] += active * a['target_visits']
        new['Каналы связи'] += active * a['target_network']
        new['Ремонт оборудования'] += active * a['target_repairs']
        new['Облачная платформа и backup'] = a['cloud_fixed']
        new['ИИ и контроль качества'] = a['ai_fixed']
        hardware = added * (a['lanes_per_store'] * a['tablet_price'] * (1 + a['tablet_spares'])
                            + a['unsupported_terminal_share'] * a['terminal_replacement'])
        new['Оборудование CapEx'] += hardware
        new['Интеграция POS HAL ERP'] = a['integration_fixed'] if m == 1 else D(0)
        new['Разработка SKU matching'] = a['sku_fixed'] if m == 1 else D(0)
        new['Миграция магазинов'] = added * a['rollout_per_store']
        new['Обучение'] = added * a['training_per_store']
        base_transition = hardware + sum(new[k] for k in CATEGORIES[9:13])
        new['Резерв рисков миграции'] = base_transition * a['contingency']
        transition_total += base_transition * (1 + a['contingency'])
        rows.append((m, active, legacy, old, new))
    old_total = sum(sum(r[3].values()) for r in rows)
    new_total = sum(sum(r[4].values()) for r in rows)
    net = old_total - new_total
    cumulative = D(0)
    breakeven = None
    for m, _, _, old, new in rows:
        delta = sum(old.values()) - sum(new.values())
        previous = cumulative
        cumulative += delta
        if previous < 0 <= cumulative and breakeven is None:
            breakeven = D(m-1) + (-previous / delta)
    annual_old = sum(rows[24][3].values()) * 12
    annual_new = sum(rows[24][4].values()) * 12
    op_old = annual_old - rows[24][3]['Оборудование CapEx'] * 12
    return rows, {
        'asis_3y': old_total, 'tobe_3y': new_total, 'net_saving': net,
        'tco_reduction_pct': net / old_total * 100,
        'transition_investment': transition_total,
        'roi_pct': net / transition_total * 100,
        'payback_month': breakeven,
        'annual_steady_asis': annual_old, 'annual_steady_tobe': annual_new,
        'steady_total_reduction_pct': (annual_old - annual_new)/annual_old*100,
        'steady_opex_reduction_pct': (op_old - annual_new)/op_old*100,
        'support_reduction_pct': (a['legacy_support']-a['target_support'])/a['legacy_support']*100,
        'target_store_months': D(sum(r[1] for r in rows)),
        'target_tco_at_40pct': old_total * D('.6'),
        'remaining_saving_for_40pct': new_total - old_total * D('.6'),
        'saas_price_ceiling_for_40pct': a['pos_saas'] - (new_total - old_total * D('.6')) / sum(r[1] for r in rows),
    }

def rounded(x):
    return '' if x is None else str(x.quantize(D('0.01')))

if __name__ == '__main__':
    rows, metrics = model()
    annual = []
    for category in CATEGORIES:
        annual.append([category] + [rounded(sum(r[idx][category] for r in rows if (r[0]-1)//12 == year))
                                    for idx in [3, 4] for year in range(3)])
    totals = [sum(D(row[col]) for row in annual) for col in range(1,7)]
    write_csv('tco.csv', ['Категория RUB', 'AS-IS Год 1', 'AS-IS Год 2', 'AS-IS Год 3',
                         'TO-BE Год 1', 'TO-BE Год 2', 'TO-BE Год 3'],
              annual + [['ИТОГО'] + [rounded(v) for v in totals]])
    cumulative = D(0)
    monthly = []
    for m, active, legacy, old, new in rows:
        old_sum, new_sum = sum(old.values()), sum(new.values())
        cumulative += old_sum-new_sum
        monthly.append([m, active, legacy, rounded(old_sum), rounded(new_sum),
                        rounded(old_sum-new_sum), rounded(cumulative)])
    write_csv('monthly-cashflow.csv', ['Месяц','Cloud магазины','Legacy с overlap','AS-IS RUB','TO-BE RUB',
                                      'Экономия RUB','Накопленная экономия RUB'], monthly)
    scenarios = [('Базовый', {}),
                 ('SaaS дороже на 30 процентов', {'pos_saas': INPUT['pos_saas'] * D('1.3')}),
                 ('ФОТ не высвобожден', {'target_support': INPUT['legacy_support']}),
                 ('Нет плановой замены серверов', {'legacy_refresh_share': D(0)}),
                 ('PaaS и ИИ дороже вдвое', {'cloud_fixed': INPUT['cloud_fixed']*2, 'ai_fixed': INPUT['ai_fixed']*2}),
                 ('Терминалы заменить в 50 процентах магазинов', {'unsupported_terminal_share': D('.5')}),
                 ('Негативный совместный', {'pos_saas': INPUT['pos_saas']*D('1.3'), 'target_support': INPUT['legacy_support'],
                                          'cloud_fixed': INPUT['cloud_fixed']*2, 'ai_fixed': INPUT['ai_fixed']*2})]
    sensitivity = []
    for name, overrides in scenarios:
        _, result = model(overrides)
        sensitivity.append([name] + [rounded(result[k]) for k in ['tobe_3y','net_saving','tco_reduction_pct','roi_pct','payback_month']])
    write_csv('sensitivity.csv', ['Сценарий','TO-BE 3 года RUB','Экономия RUB','Снижение TCO %','ROI %','Окупаемость месяц'], sensitivity)
    assert sum(totals[:3]) == metrics['asis_3y']
    assert sum(totals[3:]) == metrics['tobe_3y']
    assert rows[-1][1:3] == (100, 0)
    assert cumulative == metrics['net_saving']
    checks = [('Сумма годовых AS-IS равна помесячной','PASS'), ('Сумма годовых TO-BE равна помесячной','PASS'),
              ('После миграции 100 Cloud магазинов и 0 Legacy','PASS'), ('Накопленный поток равен экономии TCO','PASS'),
              ('Overlap учтён для всех 100 магазинов','PASS'), ('Значения допущений требуют КП и пилота','ASSUMPTION')]
    assert sum(r[2] - (100-r[1]) for r in rows) == 100
    write_csv('checks.csv', ['Проверка','Результат'], checks)
    (ROOT/'metrics.json').write_text(json.dumps({k: rounded(v) for k,v in metrics.items()},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k: rounded(v) for k,v in metrics.items()},ensure_ascii=False,indent=2))
