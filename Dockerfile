# syntax=docker/dockerfile:1
FROM docker.io/aemdesign/aem:sdk-2026.2.24464

ENV AEM_RUNMODE=-Dsling.run.modes=author,crx3,crx3tar,localdev

# AEM installs content packages from this directory during startup.
ADD --chmod=0644 --checksum=sha256:93d915fe3cbdc33b612406f1919610e8aa3fc6ffd06e25136caf49a3dec26592 https://github.com/adobe/aem-guides-wknd/releases/download/aem-guides-wknd-4.0.4/aem-guides-wknd.all-4.0.4.zip /aem/crx-quickstart/install/aem-guides-wknd.all-4.0.4.zip
