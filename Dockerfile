FROM docker.io/aemdesign/aem:sdk-2026.2.24464
ENV AEM_RUNMODE=-Dsling.run.modes=author,crx3,crx3tar,localdev
