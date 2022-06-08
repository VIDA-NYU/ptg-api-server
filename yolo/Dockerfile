FROM python:3.10

WORKDIR /src/app

ADD requirements.txt .
RUN pip install -r requirements.txt && rm -rf ~/.cache/pip /var/cache/apt/
RUN pip install -r https://raw.githubusercontent.com/ultralytics/yolov5/master/requirements.txt  # install yolo dependencies
RUN python -c "import torch;torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)"

ENV PYTHONPATH "${PYTHONPATH}:/src"

ADD ptgctl ptgctl
RUN pip install -e ./ptgctl

ADD main.py /src/app/main.py
RUN python main.py  # downloads the weights

ENTRYPOINT [ "python" ]
CMD [ "main.py", "run" ]