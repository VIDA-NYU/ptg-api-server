FROM grafana/grafana:8.5.2

USER 0

RUN apk add git curl nodejs npm
#  vim

RUN grafana-cli plugins install redis-datasource
RUN grafana-cli plugins install grafana-simple-json-datasource
# RUN grafana-cli --pluginUrl https://github.com/JamesOsgood/mongodb-grafana/zipball/master/ plugins install mongodb


ADD ./config.ini /etc/grafana/config.ini
ADD ./provisioning /etc/grafana/provisioning
ADD ./dashboards /var/lib/grafana/dashboards

# RUN git clone https://github.com/JamesOsgood/mongodb-grafana.git && mv mongodb-grafana/dist /var/lib/grafana/plugins/mongodb-datasource
# RUN sed -i 's/grafana-mongodb-datasource/mongodb-datasource/g' /var/lib/grafana/plugins/mongodb-datasource/plugin.json

RUN DEST_PATH_PREFIX='/etc/grafana/provisioning/dashboards' \
    npx grafana-dashboard-provisioner /etc/grafana/provisioning/external_dashboards  /var/lib/grafana/dashboards


USER 472