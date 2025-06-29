FROM bitnami/spark:3.5 AS spark-image

FROM python:3.13-slim AS builder-image
ARG DEBIAN_FRONTEND=noninteractive
ARG WORKDIR=/usr/src/

RUN python -m venv ${WORKDIR}/venv
ENV PATH="${WORKDIR}/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim AS app
ARG DEBIAN_FRONTEND=noninteractive
ARG WORKDIR=/usr/src/

COPY --from=builder-image ${WORKDIR}/venv ${WORKDIR}/venv
COPY --from=spark-image /opt/bitnami /opt/bitnami
RUN rm -rf /opt/bitnami/python

# copy source code
RUN mkdir ${WORKDIR}/app
RUN adduser --system --no-create-home python
COPY src ${WORKDIR}/app/src
COPY *.py ${WORKDIR}/app/

# activate nonroot user
USER python
WORKDIR ${WORKDIR}/app

# activate virtualenv
ENV VIRTUAL_ENV=${WORKDIR}/venv
ENV PATH="${WORKDIR}/venv/bin:$PATH"
ENV BITNAMI_ROOT_DIR=/opt/bitnami
ENV SPARK_HOME=$BITNAMI_ROOT_DIR/spark
ENV PATH="$PATH:$BITNAMI_ROOT_DIR/java/bin:$BITNAMI_ROOT_DIR/spark/bin:$BITNAMI_ROOT_DIR/spark/sbin"

CMD ["python", "main.py"]
