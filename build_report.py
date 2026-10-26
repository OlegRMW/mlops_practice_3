"""Build REPORT.md from actual DVC/ClearML evidence; never invent IDs or results."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def inventory(files: list[dict]) -> str:
    lines = ["| Файл | Строки × столбцы | Пропуски | SHA-256 |", "|---|---:|---:|---|"]
    for item in files:
        lines.append(f"| `{item['path']}` | {item['rows']} × {item['columns_count']} | {item['missing_values']} | `{item['sha256']}` |")
    for item in files:
        lines.append(f"\nСтолбцы `{item['path']}`: " + ", ".join(f"`{c}`" for c in item["columns"]) + ".")
        lines.append("Типы: " + ", ".join(f"`{c}: {t}`" for c, t in item["dtypes"].items()) + ".")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    def load(name):
        path = ROOT / "evidence" / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    dvc, clearml, demo = load("dvc.json"), load("clearml.json"), load("demo.json")
    if dvc and clearml:
        for label, state in [("BASE_ID", "base"), ("WINE_ID", "wine"), ("IRIS_FEATURES_ID", "iris_features")]:
            if clearml["versions"][label]["files"] != dvc[state]["files"]:
                parser.error(f"Measured DVC and ClearML contents differ: {label}")
    complete = bool(dvc and clearml and demo and demo["clearml_executed"])
    if args.require_complete and not complete:
        parser.error("Real evidence is missing: finish DVC, ClearML and demo with --clearml")
    sections = ["# Практическая работа № 3: версионирование данных", "\nАвтор: Zagudaev.",
                "\nСтатус: " + ("все локальные проверки DVC, ClearML и демонстрационного ноутбука выполнены." if complete else
                "работа не завершена; отсутствующие результаты ниже явно отмечены. Этот отчёт пока нельзя сдавать как завершённый."),
                "\n## Окружение и подготовка данных"]
    if dvc:
        sections += [f"\nPython: `{dvc['python']}`. Зависимости закреплены в `pyproject.toml` и `poetry.lock`.",
                     "\n" + ", ".join(f"{p}: `{v}`" for p, v in dvc["packages"].items()) + ".",
                     f"\nGit-репозиторий: [{dvc['repository_url']}]({dvc['repository_url']}). Основная ветка: `main`."]
    else:
        sections += ["\nТребуется Python 3.12; целевые версии: DVC 3.63.0, ClearML 2.0.2, scikit-learn 1.7.2, pandas 2.3.3. Выполнение DVC ещё не зафиксировано."]
    sections += ["\nИсточник: встроенные `load_iris(as_frame=True)` (150 строк) и `load_wine(as_frame=True)` (178 строк). "
                 "Строки стабильно сортируются по всем исходным признакам и target; порядок исходных столбцов сохранён. "
                 "CSV: UTF-8 без BOM, LF, без индекса, `float_format=\"%.15g\"`. Площади добавляются после сортировки: "
                 "`sepal_area = sepal length (cm) * sepal width (cm)`, аналогично `petal_area`.",
                 "\nКаждый режим генератора записывает только соответствующий CSV: `base` — Iris, `wine` — Wine, "
                 "`iris_features` — Iris с площадями. Для отдельного состояния используется пустая папка или DVC checkout; "
                 "генератор не удаляет соседние файлы. Проверка требует точного состава выбранного состояния.",
                 "\n`check_data.py` проверяет набор файлов, порядок столбцов и строк, исходные значения и target, типы, "
                 "пропуски, конечность чисел и обе площади. Дополнительно выводит SHA-256, форму, столбцы, типы и контрольные строки.",
                 "\n## DVC: версии, ветвление и слияние"]
    if dvc:
        sections += ["\n| Версия | Git tag | Git commit | SHA-256 `data.dvc` |",
                     "|---|---|---|---|"]
        for state, tag in [("base", "data-v1"), ("wine", "data-wine"), ("iris_features", "data-iris-features"), ("merged", "data-merged")]:
            row = dvc[state]
            sections.append(f"| {state} | `{tag}` | `{row['commit']}` | `{row['data_dvc_sha256']}` |")
        sections += [f"\nRemote `storage`: `{dvc['remote']}` — отдельная локальная директория вне Git-репозитория. "
                     "В `.dvc/config` сохранён безопасный относительный путь к соседней директории; абсолютный путь выше служит описанием расположения. На другой машине нужно отдельно перенести remote "
                     "или обеспечить доступ к сетевому хранилищу и изменить URL; GitHub сам по себе CSV не восстанавливает.",
                     "\nВ `.gitattributes`: `*.dvc merge=dvc`. В локальном Git настроен драйвер "
                     '`dvc git-hook merge-driver --ancestor %O --our %A --their %B`.',
                     f"\nВетки `feature/wine` и `feature/iris-features` созданы от `main`. После `git switch main` "
                     f"Wine ещё находился в workspace: `{dvc['stale_workspace_after_git_switch']['wine_still_exists']}`. "
                     "После `dvc checkout` Wine исчез, а базовый Iris восстановлен с исходным SHA-256.",
                     f"\nСлияние выполнено в `feature/iris-features` с `feature/wine`. Автоматический DVC merge driver успешно "
                     f"объединил разные файлы. Merge commit: `{dvc['merge']['commit']}`; два родителя: " +
                     ", ".join(f"`{p}`" for p in dvc["merge"]["parents"]) + ". Затем ветка fast-forward объединена в `main`.",
                     "\nПроверены равенство итогового Iris версии с площадями и равенство итогового Wine ветке Wine. "
                     "Маркеров конфликта нет. Для всех состояний `dvc status --json` возвращает `{}`; "
                     "после `dvc push` cloud status также `{}`. `git ls-files` не содержит CSV и cache."]
        for state in ["base", "wine", "iris_features", "merged"]:
            sections += [f"\n### Состав {state}\n", inventory(dvc[state]["files"])]
        sections += ["\n### Чистое восстановление\n",
                     f"Создан отдельный clone: `{dvc['clean_clone']['path']}`. До `dvc pull` в нём отсутствовали "
                     "`data` и `.dvc/cache`; старые workspace/cache не копировались. `dvc pull` восстановил "
                     "оба CSV из remote; полные SHA-256, формы, столбцы, типы и контрольные строки совпали с итоговым состоянием.",
                     "\nВ том же clone дополнительно по очереди восстановлены теги `data-v1`, `data-wine`, "
                     "`data-iris-features`: каждый состав совпал с ранее сохранённым состоянием. Затем восстановлен `main`. "
                     "Объекты старых версий были получены из remote, поскольку их не было в начальном cache клона."]
    else:
        sections.append("\nНе выполнено: история Git, версии DVC, remote и чистое восстановление ещё не подтверждены.")
    sections += ["\n## ClearML Dataset"]
    if clearml:
        sections += [f"\nProject: `{clearml['project']}`. Dataset name: `{clearml['name']}`.",
                     "\nСозданы три отдельные версии. Файлы загружены через `upload()` до `finalize()`; все статусы — Completed. "
                     "Исходная версия имеет тег `base`. В Wine добавлен только новый файл; неизменённый Iris "
                     "унаследован от базы, что дополнительно проверено по `file_owner_dataset_ids`.",
                     "\n| Обозначение | Version | Dataset ID | Parent IDs | Added | Modified | Removed |",
                     "|---|---|---|---|---|---|---|"]
        for label, record in clearml["versions"].items():
            sections.append(f"| `{label}` | {record['version']} | `{record['dataset_id']}` | " +
                            ", ".join(record["parents"]) + " | " + ", ".join(record["added"]) + " | " +
                            ", ".join(record["modified"]) + " | " + ", ".join(record["removed"]) + " |")
        sections += ["\nDependency graph, полученный из SDK:\n", "```json\n" + json.dumps(clearml["dependency_graph"], indent=2) + "\n```",
                     "\n```mermaid\ngraph TD\n  BASE[\"1.0.0: BASE_ID\"] --> WINE[\"1.1.0: WINE_ID\"]\n  BASE --> FEATURES[\"2.0.0: IRIS_FEATURES_ID\"]\n```",
                     "\nВсе версии повторно получены строго по ID в отдельном процессе с новым пустым ClearML cache "
                     "и скачаны в три разные пустые директории через `get_mutable_local_copy(overwrite=False)`. "
                     "Это проверка скачивания из storage на этом компьютере с чистым cache; отдельная физическая машина не использовалась. "
                     "Состав и SHA-256 всех трёх версий совпали с соответствующими DVC-состояниями."]
        for label, record in clearml["versions"].items():
            sections += [f"\n### Скачанная версия {record['version']} — `{label}`\n", inventory(record["files"]),
                         f"\n[Метаданные в ClearML UI]({record['ui_url']})."]
    else:
        sections.append("\nНе выполнено: нет подтверждённых BASE_ID, WINE_ID, IRIS_FEATURES_ID, lineage и скачанных версий. "
                        "Скрипт `run_clearml_practice.py` подготовлен; для запуска нужен настроенный доступ к серверу.")
    sections += ["\n## Сравнение по наблюдениям"]
    if dvc and clearml:
        base_id = clearml["ids"]["BASE_ID"]
        sections += ["\n| Свойство | Наблюдение DVC | Наблюдение ClearML Dataset |", "|---|---|---|"]
        rows = [
            ("Идентификатор версии", f"`data-v1` разрешается в `{dvc['base']['commit']}` и конкретный directory hash в `data.dvc`", f"База получена по `{base_id}`; её version = 1.0.0"),
            ("Метаданные", "Git сохранил четыре состояния `data.dvc`", "Три Dataset ID и их граф считаны с сервера"),
            ("Расположение файлов", "После push объекты доступны в отдельном remote storage", "upload сохранил файлы в настроенном ClearML storage; новый cache получил их повторно"),
            ("Дочерняя версия", "Две Git-ветки от main и отдельные коммиты data.dvc", "Обе дочерние версии созданы с единственным parent BASE_ID"),
            ("Переключение", "git switch оставил Wine; dvc checkout удалил его на main", "Dataset.get(dataset_id=...) восстановил каждый из трёх разных составов"),
            ("Чистая машина", "Новый clone без data/cache восстановлен dvc pull", "Отдельный процесс с пустым cache скачал все три версии; ID достаточно при доступном storage"),
            ("Ветвление", "История содержит feature/wine и feature/iris-features", "Dependency graph содержит две ветви от базы, без WINE_ID среди предков 2.0.0"),
            ("Слияние", "DVC driver объединил изменение Iris и добавление Wine; merge имеет два родителя", "Созданы две независимые дочерние версии; их слияние в этой работе не выполнялось. SDK поддерживает несколько parents, но конфликт одного файла требует явного решения"),
            ("Связь с Git", "Коммиты и теги определяют состояние data.dvc", "Получение всех версий выполнено по Dataset ID без переключения Git"),
            ("UI", "В работе использованы CLI и Git history; отдельный DVC UI не настраивался", "Сервер вернул UI-ссылки на все три Dataset, приведённые выше"),
        ]
        sections.extend(f"| {name} | {left} | {right} |" for name, left, right in rows)
    else:
        sections.append("\nТаблица наблюдений будет сформирована после реального выполнения обоих инструментов; неподтверждённые результаты не подставляются.")
    sections += ["\n## Ответы на вопросы", "\n1. **Идентификация DVC.** Конкретный Git commit фиксирует `data.dvc`, а его content hash определяет точное содержимое данных. "
                 "Сами объекты должны сохраняться в cache/remote; вместе commit, метаданные и доступное содержимое обеспечивают восстановление.",
                 "\n2. **Почему Git недостаточно.** В Git находятся код и указатели; CSV туда не добавлялись. "
                 "Без remote и при утрате локального cache новый clone не получит содержимое по одним хэшам.",
                 "\n3. **Version и ID.** Version — человекочитаемая метка, например 1.0.0; Dataset ID — однозначный идентификатор конкретного объекта сервера. "
                 "В коде скачивания используется точный ID, а не поиск только по имени/версии.",
                 "\n4. **finalize.** Он переводит текущий mutable Dataset в immutable Completed. Новый объект и новый ID "
                 "создаёт отдельный `Dataset.create`, которому передают parent ID и новый version.",
                 "\n5. **Доказательство происхождения 2.0.0.** В dependency graph значение для IRIS_FEATURES_ID должно быть ровно `[BASE_ID]`; "
                 "WINE_ID не должен встречаться среди предков. Дополнительная проверка состава: только изменённый Iris, без Wine.",
                 "\n6. **git switch без checkout.** Меняются метаданные Git, но CSV могут остаться от предыдущей ветки. "
                 "Тогда фактический workspace не соответствует data.dvc; dvc status показывает расхождение. Нужен checkout либо pull при отсутствии cache.",
                 "\n7. **Удобство.** DVC удобен для совместного изменения данных вместе с кодом в Git-ветках: в этой работе "
                 "объединяются добавление Wine и признаки Iris. ClearML Dataset удобен для независимого выбора набора "
                 "по ID и просмотра происхождения версий через сервер: две ветви lineage доступны одновременно без git switch.",
                 "\n## Демонстрационный ноутбук и проверки"]
    if demo:
        sections += [f"\nВыполнено {demo['executed_code_cells']} code cells исходного демонстрационного notebook с Digits/Diabetes. "
                     f"ClearML-часть выполнена: `{demo['clearml_executed']}`. SHA-256 файлов чистого DVC clone совпали с исходниками. "
                     "Результат: `evidence/demo.executed.ipynb`, сводка `evidence/demo.json`. Демонстрационные datasets не подменяют Iris/Wine самостоятельной работы."]
        if demo["clearml_executed"]:
            sections.append(f"\nДемонстрационные Dataset IDs: BASE `{demo['BASE_ID']}`, CHILD `{demo['CHILD_ID']}`. Они сохранены для проверки.")
    else:
        sections.append("\nДемонстрационный notebook ещё не выполнен полностью.")
    sections += ["\nПроверки генератора: повторяемость байтов всех режимов, отсутствие изменений соседнего CSV, "
                 "отдельное состояние iris_features; отклонение отсутствующего файла, индекса, потери строки, неверной площади, "
                 "target, пропуска, нарушения сортировки, лишнего столбца и бесконечного значения. Команда: `python -m unittest -v test_data`.",
                 "\nМашиночитаемые доказательства: `evidence/dvc.json`, `evidence/clearml_ids.json`, `evidence/clearml.json`, "
                 "`evidence/demo.json`. В отчёт и Git не включаются credentials, полный clearml.conf, рабочие CSV, cache и remote.",
                 "\n## Официальные источники\n",
                 "- [DVC: разрешение конфликтов метаданных](https://dvc.org/doc/user-guide/how-to/resolve-merge-conflicts)",
                 "- [ClearML Dataset API](https://clear.ml/docs/latest/docs/references/sdk/dataset/)",
                 "- [ClearML: настройка SDK](https://clear.ml/docs/latest/docs/clearml_sdk/clearml_sdk_setup/)",
                 "- [ClearML: отдельный cache через переменные окружения](https://www.clear.ml/docs/latest/docs/configs/env_vars/)"]
    (ROOT / "REPORT.md").write_text("\n".join(sections) + "\n", encoding="utf-8", newline="\n")
    print(f"REPORT.md generated. Complete evidence: {complete}")


if __name__ == "__main__":
    main()
