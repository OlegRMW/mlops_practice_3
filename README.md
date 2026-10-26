# Практика № 3 — DVC и ClearML Dataset

Локальная папка `mlops-data-zagudaev` соответствует имени из задания.
Имя удалённого GitHub-репозитория по выбору автора: `mlops_practice_3`.
Результаты и точные идентификаторы находятся в [REPORT.md](REPORT.md).

## Окружение

Python **3.12**. Все прямые версии закреплены в `pyproject.toml`, транзитивные —
в `poetry.lock`. Дополнительный pin `pathspec==0.12.1` необходим для DVC 3.63.0:
новый pathspec 1.x удалил используемый DVC внутренний `_DIR_MARK`.
Версия `dulwich==0.24.10` также закреплена: она совпадает с установленной
Git-библиотекой и совместима с используемой Poetry 2.2.1.

```powershell
poetry install --with demo
poetry run python -m unittest -v test_data
```

Для ограниченной Windows-сессии можно направить служебный индекс DVC внутрь
рабочей папки. Это не content cache и не remote:

```powershell
$env:DVC_SITE_CACHE_DIR = Join-Path (Get-Location) '.runtime/dvc_site_cache'
```

## Воспроизведение готового репозитория

Сначала клонируйте Git-репозиторий, установите зависимости и обеспечьте доступ
к содержимому DVC remote. Локальный remote находится **рядом** с репозиторием,
его точный путь указан в отчёте. Он не отправляется в GitHub. На другой машине
перенесите эту директорию или используйте сетевое хранилище:

```powershell
poetry run dvc remote modify --local storage url 'D:/path/to/copied-dvc-remote'
poetry run dvc pull
poetry run python check_data.py --state merged
```

Для локального доступа к текущему remote менять URL не требуется.

Версии: `data-v1`, `data-wine`, `data-iris-features`, `data-merged`.
После переключения Git обязательно восстановите данные:

```powershell
git switch --detach data-v1
poetry run dvc pull
poetry run python check_data.py --state base
git switch main
poetry run dvc pull
poetry run python check_data.py --state merged
```

Настройка драйвера слияния локальна для каждого клона. Если запускаете Git
вне `poetry run`, добавьте Scripts виртуального окружения в PATH:

```powershell
git config merge.dvc.name 'DVC merge driver'
git config merge.dvc.driver 'dvc git-hook merge-driver --ancestor %O --our %A --their %B'
```

## Генератор и проверка

```powershell
poetry run python prepare_data.py base
poetry run python check_data.py --state base
poetry run python prepare_data.py wine
poetry run python check_data.py --state wine
poetry run python prepare_data.py iris_features
poetry run python check_data.py --state merged
```

Каждый режим записывает только один CSV и сохраняет соседние файлы. Для ветки
с признаками без Wine сначала вернитесь к базовой версии через DVC либо
передайте генератору отдельную пустую папку через `--data-dir`.
Возможные состояния проверки: `base`, `wine`, `iris_features`, `merged`.

## ClearML

Создайте аккаунт на https://app.clear.ml, затем Settings → Workspace →
Create new credentials. Запустите `poetry run clearml-init` и вставьте
конфигурацию в локальный мастер. Credentials не помещаются в этот репозиторий.

```powershell
poetry run python run_clearml_practice.py --surname zagudaev
```

Скрипт создаёт реальные версии `1.0.0`, `1.1.0`, `2.0.0` в проекте
`MIIT/MLOps/practice_3/zagudaev`, имя Dataset: `sklearn-tabular-zagudaev`.
Обе дочерние версии происходят от базы. Неизменённый Iris повторно не
загружается в Wine. Реальные ID записываются сразу в
`evidence/clearml_ids.json`; повторный запуск продолжает незавершённую работу.
Не удаляйте этот реестр и созданные Dataset до окончания проверки.

Для скачивания уже созданных версий из нового пустого cache:

```powershell
poetry run python run_clearml_practice.py --surname zagudaev --verify-only
```

Все скачанные CSV проверяются; состав, lineage, changes, SHA-256, формы,
столбцы и типы записываются в `evidence/clearml.json`. Рабочие копии и caches
находятся в игнорируемой `.runtime`.

## Демонстрационный notebook

`demo.ipynb` — неизменённая копия выданного преподавателем примера.
Его параметры включаются только в исполняемой копии:

```powershell
poetry run python run_demo.py --surname zagudaev --clearml
```

Ячейки выполняются по порядку в одном Python-процессе, вывод и таблицы
сохраняются в `evidence/demo.executed.ipynb`. Это позволяет работать без
Jupyter kernel и открытия дополнительных портов. Самостоятельная работа
использует Iris/Wine, демонстрация — Digits/Diabetes и отдельные ClearML names.

## Полный запуск и отчёт

Сценарий DVC `run_dvc_practice.py` запускается **один раз** в новой Git-папке
после создания `poetry.lock`. Существующие данные, историю Git, непустой remote
и clone он не перезаписывает. После раннего сбоя можно продолжить только пустой
Git-репозиторий без коммитов, refs и данных, с пустым remote. В индексе
допускаются только три служебных файла, автоматически добавленные `dvc init`.
Следующая команда выполняет недостающие этапы, формирует отчёт
только после реальных проверок и, с флагом `--push`, отправляет Git-ветки и теги:

```powershell
poetry run python finish_practice.py --repository-url https://github.com/YOUR_USER/mlops_practice_3.git --push
```

Для одной только повторной генерации отчёта:

```powershell
poetry run python build_report.py --require-complete
```

В Windows папка, созданная Codex, может принадлежать другой служебной учётной
записи. Если Git сообщает `dubious ownership`, сценарий добавляет в глобальный
`safe.directory` только точный путь используемого репозитория или его клона.
Это также применяется к отдельным папкам демонстрационного notebook.

Remote настраивается относительным путём `../dvc-remote-zagudaev`: DVC сохраняет
его относительно `.dvc/config`, поэтому в файле получается
`../../dvc-remote-zagudaev`. Это позволяет работать с кириллицей в родительском
пути даже при ASCII-сериализации ConfigObj в DVC 3.63.0. Такая же адаптация
применяется к remote в исполняемой копии демонстрационного notebook.

Сдавайте Git-репозиторий с историей и отчётом. CSV, `.runtime`, DVC cache,
внешний local remote, `.venv` и `clearml.conf` не включаются. ClearML datasets
на сервере сохраняются до проверки. Один архив исходников без `.git` не
сохранит требуемую историю веток.
