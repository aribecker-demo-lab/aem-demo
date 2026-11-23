# syntax=docker/dockerfile:1
FROM maven:3.9.9-eclipse-temurin-17 AS weather-backend
WORKDIR /build
COPY weather/pom.xml ./
COPY weather/src ./src
RUN mvn --batch-mode --no-transfer-progress package

FROM python:3.12-slim AS content-package

ADD --chmod=0644 --checksum=sha256:93d915fe3cbdc33b612406f1919610e8aa3fc6ffd06e25136caf49a3dec26592 https://github.com/adobe/aem-guides-wknd/releases/download/aem-guides-wknd-4.0.4/aem-guides-wknd.all-4.0.4.zip /tmp/aem-guides-wknd.all-4.0.4.zip
COPY content-package/build.py /tmp/build.py
COPY weather/component /tmp/weather/component
COPY weather/clientlib /tmp/weather/clientlib
RUN python /tmp/build.py /tmp/aem-guides-wknd.all-4.0.4.zip /tmp/wknd-demo-adventure-1.0.0.zip --weather-source /tmp/weather

FROM docker.io/aemdesign/aem:sdk-2026.2.24464

ENV AEM_RUNMODE=-Dsling.run.modes=author,crx3,crx3tar,localdev

COPY --from=content-package /tmp/aem-guides-wknd.all-4.0.4.zip /aem/crx-quickstart/install/
COPY --from=content-package /tmp/wknd-demo-adventure-1.0.0.zip /aem/crx-quickstart/install/
COPY --from=weather-backend /build/target/weather-1.0.0.jar /aem/crx-quickstart/install/
