FROM ajeje93/grafana-mongodb

#FROM grafana/grafana:8.5.2
#COPY --from=mongogf /custom-run.sh /custom-run.sh
#COPY --from=mongogf $GF_PATHS_PLUGINS/mongodb-grafana $GF_PATHS_PLUGINS/mongodb-grafana

USER 0

RUN apk add git curl nodejs npm

ADD ./provisioning /etc/grafana/provisioning
RUN DEST_PATH_PREFIX='/etc/grafana/provisioning/dashboards' \
    npx grafana-dashboard-provisioner \
        /etc/grafana/provisioning/external_dashboards  \
        /etc/grafana/provisioning/dashboards

USER 472

RUN grafana-cli plugins install redis-datasource
RUN grafana-cli plugins install grafana-simple-json-datasource
RUN grafana-cli plugins install redis-app

ADD ./config.ini /etc/grafana/config.ini

ADD ./dashboards /var/lib/grafana/dashboards

ENTRYPOINT ["/custom-run.sh"]
