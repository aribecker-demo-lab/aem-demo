# syntax=docker/dockerfile:1
FROM maven:3.9.9-eclipse-temurin-17 AS weather-backend
WORKDIR /build
COPY weather/pom.xml ./
COPY weather/src ./src
RUN printf '%s\tDocker\tWeather bundle\t—\t—\tPending\tBuilding\tMaven build started\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /build/weather-timeline.tsv \
    && (mvn --batch-mode --no-transfer-progress package > /build/weather-build.log 2>&1 || { cat /build/weather-build.log; exit 1; }) \
    && cat /build/weather-build.log \
    && printf '%s\tDocker\tWeather bundle\t—\t—\tBuilding\tBuilt\tMaven build and tests passed\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /build/weather-timeline.tsv

FROM maven:3.9.9-eclipse-temurin-17 AS lifecycle-backend
WORKDIR /build
COPY lifecycle/pom.xml ./
COPY lifecycle/src ./src
RUN mvn --batch-mode --no-transfer-progress package \
    && printf '%s\tDocker\tLifecycle observer\t—\t—\tBuilding\tBuilt\tObserver bundle packaged\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /build/lifecycle-timeline.tsv

FROM python:3.12-slim AS content-package

ADD --chmod=0644 --checksum=sha256:93d915fe3cbdc33b612406f1919610e8aa3fc6ffd06e25136caf49a3dec26592 https://github.com/adobe/aem-guides-wknd/releases/download/aem-guides-wknd-4.0.4/aem-guides-wknd.all-4.0.4.zip /tmp/aem-guides-wknd.all-4.0.4.zip
COPY content-package/build.py /tmp/build.py
COPY content-package/demo-components.jpg /tmp/demo-components.jpg
COPY content-package/catalog-images /tmp/catalog-images
COPY weather/pom.xml /tmp/weather/pom.xml
COPY weather/src/main/java /tmp/weather/src/main/java
COPY --from=weather-backend /build/target/weather-1.0.0.jar /tmp/weather-bundle.jar
COPY weather/component /tmp/weather/component
COPY weather/system-logs /tmp/weather/system-logs
COPY weather/clientlib /tmp/weather/clientlib
COPY react-index /tmp/react-index
RUN python /tmp/build.py /tmp/aem-guides-wknd.all-4.0.4.zip /tmp/wknd-demo-adventure-1.0.0.zip --weather-source /tmp/weather --section-image /tmp/demo-components.jpg --weather-bundle /tmp/weather-bundle.jar --react-source /tmp/react-index
RUN printf '%s\tDocker\tWKND and demo packages\t—\t—\tBuilding\tBuilt\tVerified WKND archive and generated FileVault package\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /tmp/content-timeline.tsv
RUN printf "BUILD WKND: Verified WKND 4.0.4 archive SHA-256\nBUILD DEMO: Generated FileVault content package\n" > /tmp/content-build.log

FROM docker.io/aemdesign/aem:sdk-2026.2.24464

ENV AEM_RUNMODE=-Dsling.run.modes=author,crx3,crx3tar,localdev

COPY --from=content-package /tmp/aem-guides-wknd.all-4.0.4.zip /aem/crx-quickstart/install/
COPY --from=content-package /tmp/wknd-demo-adventure-1.0.0.zip /aem/crx-quickstart/install/
COPY --from=lifecycle-backend /build/target/lifecycle-1.0.0.jar /aem/crx-quickstart/install/
COPY --from=weather-backend /build/target/weather-1.0.0.jar /aem/crx-quickstart/install/
COPY --from=weather-backend /build/weather-build.log /opt/wknd-diagnostics/weather-build.log
COPY --from=content-package /tmp/content-build.log /opt/wknd-diagnostics/content-build.log
RUN cat /opt/wknd-diagnostics/weather-build.log /opt/wknd-diagnostics/content-build.log > /opt/wknd-diagnostics/build.log && printf 'BUILD IMAGE: Staged both content packages and the OSGi bundle\n' >> /opt/wknd-diagnostics/build.log

COPY --from=weather-backend /build/weather-timeline.tsv /opt/wknd-diagnostics/weather-timeline.tsv
COPY --from=lifecycle-backend /build/lifecycle-timeline.tsv /opt/wknd-diagnostics/lifecycle-timeline.tsv
COPY --from=content-package /tmp/content-timeline.tsv /opt/wknd-diagnostics/content-timeline.tsv
RUN cat /opt/wknd-diagnostics/weather-timeline.tsv /opt/wknd-diagnostics/lifecycle-timeline.tsv /opt/wknd-diagnostics/content-timeline.tsv > /opt/wknd-diagnostics/build-timeline.tsv \
    && printf '%s\tDocker\tAEM image\t—\t—\tBuilding\tStaged\tAEM image layers staged with packages and bundles\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /opt/wknd-diagnostics/build-timeline.tsv
