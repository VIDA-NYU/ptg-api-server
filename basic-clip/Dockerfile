FROM ptgctl

WORKDIR /src/app

RUN apt-get update && apt-get install -y python3-opencv git && rm -rf /var/lib/apt/lists/*

ADD requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

ADD main.py .
CMD ["main.py", "run"]
