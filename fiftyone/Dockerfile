FROM python:3.10-slim
WORKDIR /src

RUN pip --no-cache-dir install -U pip ipython fiftyone
ADD app.py .

EXPOSE 5151
CMD ["python", "app.py"]
