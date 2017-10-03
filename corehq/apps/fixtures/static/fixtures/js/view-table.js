define([
    "jquery",
    "hqwebapp/js/django",
    "hqwebapp/js/bundle",
    "fixtures/js/bundle",
], function(
    $,
    django,
    hq,
    fixtures
) {
    if (hq.initialPageData.get('renderReportTables')) {
        var reportTables = fixtures.datatablesConfig.HQReportDataTables(hq.initialPageData.get('dataTablesOptions')),
            standardHQReport = fixtures.standardHQReportModule.getStandardHQReport();
        if (typeof standardHQReport !== 'undefined') {
            standardHQReport.handleTabularReportCookies(reportTables);
        }
        reportTables.render();
    }

    fixtures.filters.init();

    $(function() {
        $('.header-popover').popover({
            trigger: 'hover',
            placement: 'bottom',
        });
    });
});
