FROM python:3.9
WORKDIR /opt
RUN pip3 install poetry
COPY . .
RUN poetry install
ENTRYPOINT ["poetry", "run", "main.py"]