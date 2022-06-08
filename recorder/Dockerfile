FROM python:3.10

WORKDIR /src/app

ADD requirements.txt .
RUN pip install -r requirements.txt && rm -rf ~/.cache/pip /var/cache/apt/

ENV PYTHONPATH "${PYTHONPATH}:/src"

ADD ptgctl ptgctl
RUN pip install -e ./ptgctl

ADD main.py /src/app/main.py

ENTRYPOINT [ "python" ]
CMD [ "main.py", "run" ]