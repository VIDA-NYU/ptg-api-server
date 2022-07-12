#FROM python:3.10
FROM ptgctl

#WORKDIR /src/app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt autoremove && apt clean && \
    rm -rf /var/lib/apt/lists/*

ADD requirements.txt .
RUN pip install -r requirements.txt && rm -rf ~/.cache/pip /var/cache/apt/

#ENV PYTHONPATH "${PYTHONPATH}:/src"

#ADD ptgctl ptgctl
#RUN pip install -e ./ptgctl

ADD main.py /src/app/main.py

#ENTRYPOINT [ "python" ]
CMD [ "main.py", "run" ]
