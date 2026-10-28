# Задание 3 — облачная касса и оборудование

| Материал | Назначение |
|---|---|
| [discovery.md](discovery.md) | Проверка достоверности артефактов и исправления AS-IS |
| [architecture.md](architecture.md) | Cloud POS, HAL, PaaS, границы данных, план миграции и тесты |
| [offline-sync.md](offline-sync.md) | Три абзаца о работе без сети и восстановлении синхронизации |
| AS-IS: [PNG](diagrams/as-is.png), [SVG](diagrams/as-is.svg), [PlantUML](diagrams/as-is.puml) | Исправленная C4 Container схема |
| TO-BE: [PNG](diagrams/to-be.png), [SVG](diagrams/to-be.svg), [PlantUML](diagrams/to-be.puml) | HLD с границами Store / Cloud / HQ и локальным HAL |

Диаграммы используют локальную C4-PlantUML v2.12.0 из корневого `Diagrams/vendor/`, рендерятся без GitHub и Graphviz. При переносе нужно сохранить этот путь относительно `VitaStore/Task3/diagrams/`.
