FROM python:3.10
# opencv is installed then uninstalled apparently because it gives us some dependencies that we need
# then we reinstall opencv using pip. Idk ask the original authors
RUN apt-get update -qyy && \
    apt-get install -y  python3-opencv && apt-get remove -y python3-opencv \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ADD requirements.txt .
RUN pip install -r requirements.txt && rm -rf ~/.cache/pip /var/cache/apt/

ADD . /app
ENTRYPOINT [ "python", "-m" ]
CMD [ "gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000" ]