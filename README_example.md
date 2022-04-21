# Teeth movement

Package for teeth movement prediction.

## Table of Contents

- [Dependencies](#markdown-header-dependencies)
- [Install](#markdown-header-install)
- [Build](#markdown-header-build)
- [Example usage](#markdown-header-example-usage)
- [Build docs](#markdown-header-build-docs)
- [Running in docker](#markdown-header-running-in-docker)

## Dependencies

- python 3.6 or later
- 

## Install dependance

```bash
sudo apt-get install -y python3.6 python3.6-dev python3-pip python3.6-venv
python3 -m pip install pip --upgrade
```
## Build

### in container [нам не надо]
```
./build.sh
```

### Build locally for development purposes (locally)

Setup virtualenv

```bash
python3 -m venv ~/virtualenv/silines_temp
source ~/virtualenv/tmov/bin/activate
pip3 install wheel
pip3 install -r requirements.txt
```

The following command will install development version of package.

```bash
python3 setup.py develop
```

or to build binary run

```
python3 setup.py bdist_wheel
```

## Example usage


```bash
python3 TempScanner.py
```

Запуск для конфигурирования модуля

```bash
python3 TempScanner.py -C
```

Последовательность настройки:

```bash
python3 TempScanner.py -h
python3 TempScanner.py -С
cp .... ...
```

Docker run example:

```bash
docker-compose up -d
docker exec -it TempScanner.py bash
ls
```

all test:

```


```

## Build docs

### Build docs locally

Create docx directory

```bash
mkdir -p docx
```

#### python API docs

```bash
cp docs
make html
```

Docs will be located in docx/py/html


## Running in docker

Dependencies: `docker` and `docker-compose`

Start the docker daemon:
```bash
systemctl enable --now docker.service
```

Enter the container with all dependencies installed:

```bash
docker-compose up -d
docker exec -it teeth_movement bash
ls
```

## Редактирование конфигурационного файла:

читать config.json.md


