FROM python:3.12

COPY main.py main.py
COPY models.py models.py
COPY .env .env

RUN pip install --upgrade pip
RUN pip install fastapi[standard]
RUN pip install sqlalchemy
RUN pip install python-jose
RUN pip install dotenv
RUN pip install passlib
RUN pip install sqlmodel
RUN pip install numpy
RUN pip install uuid
RUN pip install typing

EXPOSE 8000

CMD ["fastapi", "dev", "main.py"]
