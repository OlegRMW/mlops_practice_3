# Практическая работа № 3: версионирование данных

Автор: Zagudaev.

Статус: все локальные проверки DVC, ClearML и демонстрационного ноутбука выполнены.

## Окружение и подготовка данных

Python: `3.12.5`. Зависимости закреплены в `pyproject.toml` и `poetry.lock`.

dvc: `3.63.0`, clearml: `2.0.2`, scikit-learn: `1.7.2`, pandas: `2.3.3`, numpy: `2.5.4`, poetry: `2.2.1`, pathspec: `0.12.1`.

Git-репозиторий: [https://github.com/OlegRMW/mlops_practice_3.git](https://github.com/OlegRMW/mlops_practice_3.git). Основная ветка: `main`.

Источник: встроенные `load_iris(as_frame=True)` (150 строк) и `load_wine(as_frame=True)` (178 строк). Строки стабильно сортируются по всем исходным признакам и target; порядок исходных столбцов сохранён. CSV: UTF-8 без BOM, LF, без индекса, `float_format="%.15g"`. Площади добавляются после сортировки: `sepal_area = sepal length (cm) * sepal width (cm)`, аналогично `petal_area`.

Каждый режим генератора записывает только соответствующий CSV: `base` — Iris, `wine` — Wine, `iris_features` — Iris с площадями. Для отдельного состояния используется пустая папка или DVC checkout; генератор не удаляет соседние файлы. Проверка требует точного состава выбранного состояния.

`check_data.py` проверяет набор файлов, порядок столбцов и строк, исходные значения и target, типы, пропуски, конечность чисел и обе площади. Дополнительно выводит SHA-256, форму, столбцы, типы и контрольные строки.

## DVC: версии, ветвление и слияние

| Версия | Git tag | Git commit | SHA-256 `data.dvc` |
|---|---|---|---|
| base | `data-v1` | `5cf56483cd053f6b4cd4a9e7ec3b7f8f0f008cb0` | `e3eb120698a91fa79bf9691ab113c12fcdc9e318279ca93d7f03dfd55db40b12` |
| wine | `data-wine` | `0cbf25bebefebed17b89e614164909c14397d720` | `4be01c9b3c491782bb0423347d339b02fce9269c28c5748ee5a0a76a63399bd9` |
| iris_features | `data-iris-features` | `f56b2feb51840e0528dd4c6b4470ac541f3fb3fc` | `7f92f23a0d38867c92d3d2b9d0ebac2eee803dd6233cba2146082a61a77d9cbe` |
| merged | `data-merged` | `d50a41d3b3938260617e0692e0af2c19f18410b8` | `96dfda4219f2457ea0fdce7cb7d69cb89dd0e55680d6be9b639f3f5624c1aefb` |

Remote `storage`: `C:/Users/Admin/Desktop/практика_3_mlops/dvc-remote-zagudaev` — отдельная локальная директория вне Git-репозитория. В `.dvc/config` сохранён безопасный относительный путь к соседней директории; абсолютный путь выше служит описанием расположения. На другой машине нужно отдельно перенести remote или обеспечить доступ к сетевому хранилищу и изменить URL; GitHub сам по себе CSV не восстанавливает.

В `.gitattributes`: `*.dvc merge=dvc`. В локальном Git настроен драйвер `dvc git-hook merge-driver --ancestor %O --our %A --their %B`.

Ветки `feature/wine` и `feature/iris-features` созданы от `main`. После `git switch main` Wine ещё находился в workspace: `True`. После `dvc checkout` Wine исчез, а базовый Iris восстановлен с исходным SHA-256.

Слияние выполнено в `feature/iris-features` с `feature/wine`. Автоматический DVC merge driver успешно объединил разные файлы. Merge commit: `d50a41d3b3938260617e0692e0af2c19f18410b8`; два родителя: `f56b2feb51840e0528dd4c6b4470ac541f3fb3fc`, `0cbf25bebefebed17b89e614164909c14397d720`. Затем ветка fast-forward объединена в `main`.

Проверены равенство итогового Iris версии с площадями и равенство итогового Wine ветке Wine. Маркеров конфликта нет. Для всех состояний `dvc status --json` возвращает `{}`; после `dvc push` cloud status также `{}`. `git ls-files` не содержит CSV и cache.

### Состав base

| Файл | Строки × столбцы | Пропуски | SHA-256 |
|---|---:|---:|---|
| `data/iris.csv` | 150 × 5 | 0 | `6d700503c9c2e2c71d187b889a87af8a8d3a6dd5bae1266d46f4ee4db5a6349f` |

Столбцы `data/iris.csv`: `sepal length (cm)`, `sepal width (cm)`, `petal length (cm)`, `petal width (cm)`, `target`.
Типы: `sepal length (cm): float64`, `sepal width (cm): float64`, `petal length (cm): float64`, `petal width (cm): float64`, `target: int64`.

### Состав wine

| Файл | Строки × столбцы | Пропуски | SHA-256 |
|---|---:|---:|---|
| `data/iris.csv` | 150 × 5 | 0 | `6d700503c9c2e2c71d187b889a87af8a8d3a6dd5bae1266d46f4ee4db5a6349f` |
| `data/wine.csv` | 178 × 14 | 0 | `38860ba04ace4d402242340bcf40be4bd6f4ebde9144a3dc89dc12c20f7f8e60` |

Столбцы `data/iris.csv`: `sepal length (cm)`, `sepal width (cm)`, `petal length (cm)`, `petal width (cm)`, `target`.
Типы: `sepal length (cm): float64`, `sepal width (cm): float64`, `petal length (cm): float64`, `petal width (cm): float64`, `target: int64`.

Столбцы `data/wine.csv`: `alcohol`, `malic_acid`, `ash`, `alcalinity_of_ash`, `magnesium`, `total_phenols`, `flavanoids`, `nonflavanoid_phenols`, `proanthocyanins`, `color_intensity`, `hue`, `od280/od315_of_diluted_wines`, `proline`, `target`.
Типы: `alcohol: float64`, `malic_acid: float64`, `ash: float64`, `alcalinity_of_ash: float64`, `magnesium: int64`, `total_phenols: float64`, `flavanoids: float64`, `nonflavanoid_phenols: float64`, `proanthocyanins: float64`, `color_intensity: float64`, `hue: float64`, `od280/od315_of_diluted_wines: float64`, `proline: int64`, `target: int64`.

### Состав iris_features

| Файл | Строки × столбцы | Пропуски | SHA-256 |
|---|---:|---:|---|
| `data/iris.csv` | 150 × 7 | 0 | `3e1ba63f55da2aabc432d00b1670140f5162bf9ef34b837598ec2fc176c9ff26` |

Столбцы `data/iris.csv`: `sepal length (cm)`, `sepal width (cm)`, `petal length (cm)`, `petal width (cm)`, `target`, `sepal_area`, `petal_area`.
Типы: `sepal length (cm): float64`, `sepal width (cm): float64`, `petal length (cm): float64`, `petal width (cm): float64`, `target: int64`, `sepal_area: float64`, `petal_area: float64`.

### Состав merged

| Файл | Строки × столбцы | Пропуски | SHA-256 |
|---|---:|---:|---|
| `data/iris.csv` | 150 × 7 | 0 | `3e1ba63f55da2aabc432d00b1670140f5162bf9ef34b837598ec2fc176c9ff26` |
| `data/wine.csv` | 178 × 14 | 0 | `38860ba04ace4d402242340bcf40be4bd6f4ebde9144a3dc89dc12c20f7f8e60` |

Столбцы `data/iris.csv`: `sepal length (cm)`, `sepal width (cm)`, `petal length (cm)`, `petal width (cm)`, `target`, `sepal_area`, `petal_area`.
Типы: `sepal length (cm): float64`, `sepal width (cm): float64`, `petal length (cm): float64`, `petal width (cm): float64`, `target: int64`, `sepal_area: float64`, `petal_area: float64`.

Столбцы `data/wine.csv`: `alcohol`, `malic_acid`, `ash`, `alcalinity_of_ash`, `magnesium`, `total_phenols`, `flavanoids`, `nonflavanoid_phenols`, `proanthocyanins`, `color_intensity`, `hue`, `od280/od315_of_diluted_wines`, `proline`, `target`.
Типы: `alcohol: float64`, `malic_acid: float64`, `ash: float64`, `alcalinity_of_ash: float64`, `magnesium: int64`, `total_phenols: float64`, `flavanoids: float64`, `nonflavanoid_phenols: float64`, `proanthocyanins: float64`, `color_intensity: float64`, `hue: float64`, `od280/od315_of_diluted_wines: float64`, `proline: int64`, `target: int64`.

### Чистое восстановление

Создан отдельный clone: `C:/Users/Admin/Desktop/практика_3_mlops/clean-clone-zagudaev`. До `dvc pull` в нём отсутствовали `data` и `.dvc/cache`; старые workspace/cache не копировались. `dvc pull` восстановил оба CSV из remote; полные SHA-256, формы, столбцы, типы и контрольные строки совпали с итоговым состоянием.

В том же clone дополнительно по очереди восстановлены теги `data-v1`, `data-wine`, `data-iris-features`: каждый состав совпал с ранее сохранённым состоянием. Затем восстановлен `main`. Объекты старых версий были получены из remote, поскольку их не было в начальном cache клона.

## ClearML Dataset

Project: `MIIT/MLOps/practice_3/zagudaev`. Dataset name: `sklearn-tabular-zagudaev`.

Созданы три отдельные версии. Файлы загружены через `upload()` до `finalize()`; все статусы — Completed. Исходная версия имеет тег `base`. В Wine добавлен только новый файл; неизменённый Iris унаследован от базы, что дополнительно проверено по `file_owner_dataset_ids`.

| Обозначение | Version | Dataset ID | Parent IDs | Added | Modified | Removed |
|---|---|---|---|---|---|---|
| `BASE_ID` | 1.0.0 | `0c3ab7bf5e7b46e9b448249dd5a71103` |  | iris.csv |  |  |
| `WINE_ID` | 1.1.0 | `73fd53584c064ba0a45c3187f3e7af98` | 0c3ab7bf5e7b46e9b448249dd5a71103 | wine.csv |  |  |
| `IRIS_FEATURES_ID` | 2.0.0 | `ad76a5e5fb044c71af432a1c612207e2` | 0c3ab7bf5e7b46e9b448249dd5a71103 |  | iris.csv |  |

Dependency graph, полученный из SDK:

```json
{
  "0c3ab7bf5e7b46e9b448249dd5a71103": [],
  "73fd53584c064ba0a45c3187f3e7af98": [
    "0c3ab7bf5e7b46e9b448249dd5a71103"
  ],
  "ad76a5e5fb044c71af432a1c612207e2": [
    "0c3ab7bf5e7b46e9b448249dd5a71103"
  ]
}
```

```mermaid
graph TD
  BASE["1.0.0: BASE_ID"] --> WINE["1.1.0: WINE_ID"]
  BASE --> FEATURES["2.0.0: IRIS_FEATURES_ID"]
```

Все версии повторно получены строго по ID в отдельном процессе с новым пустым ClearML cache и скачаны в три разные пустые директории через `get_mutable_local_copy(overwrite=False)`. Это проверка скачивания из storage на этом компьютере с чистым cache; отдельная физическая машина не использовалась. Состав и SHA-256 всех трёх версий совпали с соответствующими DVC-состояниями.

### Скачанная версия 1.0.0 — `BASE_ID`

| Файл | Строки × столбцы | Пропуски | SHA-256 |
|---|---:|---:|---|
| `data/iris.csv` | 150 × 5 | 0 | `6d700503c9c2e2c71d187b889a87af8a8d3a6dd5bae1266d46f4ee4db5a6349f` |

Столбцы `data/iris.csv`: `sepal length (cm)`, `sepal width (cm)`, `petal length (cm)`, `petal width (cm)`, `target`.
Типы: `sepal length (cm): float64`, `sepal width (cm): float64`, `petal length (cm): float64`, `petal width (cm): float64`, `target: int64`.

[Метаданные в ClearML UI](https://app.clear.ml/projects/2decfa37e9e34832bed1134763d925dd/experiments/0c3ab7bf5e7b46e9b448249dd5a71103/output/log).

### Скачанная версия 1.1.0 — `WINE_ID`

| Файл | Строки × столбцы | Пропуски | SHA-256 |
|---|---:|---:|---|
| `data/iris.csv` | 150 × 5 | 0 | `6d700503c9c2e2c71d187b889a87af8a8d3a6dd5bae1266d46f4ee4db5a6349f` |
| `data/wine.csv` | 178 × 14 | 0 | `38860ba04ace4d402242340bcf40be4bd6f4ebde9144a3dc89dc12c20f7f8e60` |

Столбцы `data/iris.csv`: `sepal length (cm)`, `sepal width (cm)`, `petal length (cm)`, `petal width (cm)`, `target`.
Типы: `sepal length (cm): float64`, `sepal width (cm): float64`, `petal length (cm): float64`, `petal width (cm): float64`, `target: int64`.

Столбцы `data/wine.csv`: `alcohol`, `malic_acid`, `ash`, `alcalinity_of_ash`, `magnesium`, `total_phenols`, `flavanoids`, `nonflavanoid_phenols`, `proanthocyanins`, `color_intensity`, `hue`, `od280/od315_of_diluted_wines`, `proline`, `target`.
Типы: `alcohol: float64`, `malic_acid: float64`, `ash: float64`, `alcalinity_of_ash: float64`, `magnesium: int64`, `total_phenols: float64`, `flavanoids: float64`, `nonflavanoid_phenols: float64`, `proanthocyanins: float64`, `color_intensity: float64`, `hue: float64`, `od280/od315_of_diluted_wines: float64`, `proline: int64`, `target: int64`.

[Метаданные в ClearML UI](https://app.clear.ml/projects/2decfa37e9e34832bed1134763d925dd/experiments/73fd53584c064ba0a45c3187f3e7af98/output/log).

### Скачанная версия 2.0.0 — `IRIS_FEATURES_ID`

| Файл | Строки × столбцы | Пропуски | SHA-256 |
|---|---:|---:|---|
| `data/iris.csv` | 150 × 7 | 0 | `3e1ba63f55da2aabc432d00b1670140f5162bf9ef34b837598ec2fc176c9ff26` |

Столбцы `data/iris.csv`: `sepal length (cm)`, `sepal width (cm)`, `petal length (cm)`, `petal width (cm)`, `target`, `sepal_area`, `petal_area`.
Типы: `sepal length (cm): float64`, `sepal width (cm): float64`, `petal length (cm): float64`, `petal width (cm): float64`, `target: int64`, `sepal_area: float64`, `petal_area: float64`.

[Метаданные в ClearML UI](https://app.clear.ml/projects/2decfa37e9e34832bed1134763d925dd/experiments/ad76a5e5fb044c71af432a1c612207e2/output/log).

## Сравнение по наблюдениям

| Свойство | Наблюдение DVC | Наблюдение ClearML Dataset |
|---|---|---|
| Идентификатор версии | `data-v1` разрешается в `5cf56483cd053f6b4cd4a9e7ec3b7f8f0f008cb0` и конкретный directory hash в `data.dvc` | База получена по `0c3ab7bf5e7b46e9b448249dd5a71103`; её version = 1.0.0 |
| Метаданные | Git сохранил четыре состояния `data.dvc` | Три Dataset ID и их граф считаны с сервера |
| Расположение файлов | После push объекты доступны в отдельном remote storage | upload сохранил файлы в настроенном ClearML storage; новый cache получил их повторно |
| Дочерняя версия | Две Git-ветки от main и отдельные коммиты data.dvc | Обе дочерние версии созданы с единственным parent BASE_ID |
| Переключение | git switch оставил Wine; dvc checkout удалил его на main | Dataset.get(dataset_id=...) восстановил каждый из трёх разных составов |
| Чистая машина | Новый clone без data/cache восстановлен dvc pull | Отдельный процесс с пустым cache скачал все три версии; ID достаточно при доступном storage |
| Ветвление | История содержит feature/wine и feature/iris-features | Dependency graph содержит две ветви от базы, без WINE_ID среди предков 2.0.0 |
| Слияние | DVC driver объединил изменение Iris и добавление Wine; merge имеет два родителя | Созданы две независимые дочерние версии; их слияние в этой работе не выполнялось. SDK поддерживает несколько parents, но конфликт одного файла требует явного решения |
| Связь с Git | Коммиты и теги определяют состояние data.dvc | Получение всех версий выполнено по Dataset ID без переключения Git |
| UI | В работе использованы CLI и Git history; отдельный DVC UI не настраивался | Сервер вернул UI-ссылки на все три Dataset, приведённые выше |

## Ответы на вопросы

1. **Идентификация DVC.** Конкретный Git commit фиксирует `data.dvc`, а его content hash определяет точное содержимое данных. Сами объекты должны сохраняться в cache/remote; вместе commit, метаданные и доступное содержимое обеспечивают восстановление.

2. **Почему Git недостаточно.** В Git находятся код и указатели; CSV туда не добавлялись. Без remote и при утрате локального cache новый clone не получит содержимое по одним хэшам.

3. **Version и ID.** Version — человекочитаемая метка, например 1.0.0; Dataset ID — однозначный идентификатор конкретного объекта сервера. В коде скачивания используется точный ID, а не поиск только по имени/версии.

4. **finalize.** Он переводит текущий mutable Dataset в immutable Completed. Новый объект и новый ID создаёт отдельный `Dataset.create`, которому передают parent ID и новый version.

5. **Доказательство происхождения 2.0.0.** В dependency graph значение для IRIS_FEATURES_ID должно быть ровно `[BASE_ID]`; WINE_ID не должен встречаться среди предков. Дополнительная проверка состава: только изменённый Iris, без Wine.

6. **git switch без checkout.** Меняются метаданные Git, но CSV могут остаться от предыдущей ветки. Тогда фактический workspace не соответствует data.dvc; dvc status показывает расхождение. Нужен checkout либо pull при отсутствии cache.

7. **Удобство.** DVC удобен для совместного изменения данных вместе с кодом в Git-ветках: в этой работе объединяются добавление Wine и признаки Iris. ClearML Dataset удобен для независимого выбора набора по ID и просмотра происхождения версий через сервер: две ветви lineage доступны одновременно без git switch.

## Демонстрационный ноутбук и проверки

Выполнено 14 code cells исходного демонстрационного notebook с Digits/Diabetes. ClearML-часть выполнена: `True`. SHA-256 файлов чистого DVC clone совпали с исходниками. Результат: `evidence/demo.executed.ipynb`, сводка `evidence/demo.json`. Демонстрационные datasets не подменяют Iris/Wine самостоятельной работы.

Демонстрационные Dataset IDs: BASE `887a6d98ab0749d99e2aa66f35572769`, CHILD `a8a770d1680d45d3962eae0838578416`. Они сохранены для проверки.

Проверки генератора: повторяемость байтов всех режимов, отсутствие изменений соседнего CSV, отдельное состояние iris_features; отклонение отсутствующего файла, индекса, потери строки, неверной площади, target, пропуска, нарушения сортировки, лишнего столбца и бесконечного значения. Команда: `python -m unittest -v test_data`.

Машиночитаемые доказательства: `evidence/dvc.json`, `evidence/clearml_ids.json`, `evidence/clearml.json`, `evidence/demo.json`. В отчёт и Git не включаются credentials, полный clearml.conf, рабочие CSV, cache и remote.

## Официальные источники

- [DVC: разрешение конфликтов метаданных](https://dvc.org/doc/user-guide/how-to/resolve-merge-conflicts)
- [ClearML Dataset API](https://clear.ml/docs/latest/docs/references/sdk/dataset/)
- [ClearML: настройка SDK](https://clear.ml/docs/latest/docs/clearml_sdk/clearml_sdk_setup/)
- [ClearML: отдельный cache через переменные окружения](https://www.clear.ml/docs/latest/docs/configs/env_vars/)
