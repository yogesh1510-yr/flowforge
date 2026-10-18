FROM apache/spark:3.5.1

USER root
RUN python3 -m pip install --no-cache-dir "psycopg[binary]>=3.2,<4.0"
COPY src/flowforge /opt/flowforge/src/flowforge
ENV PYTHONPATH=/opt/flowforge/src

