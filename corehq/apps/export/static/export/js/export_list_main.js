hqDefine("export/js/export_list_main", [
    'jquery',
    'hqwebapp/js/initial_page_data',
    'analytix/js/kissmetrix',
    'hqwebapp/js/main',
    'export/js/create_export',
    'export/js/export_list',
    'hqwebapp/js/select_2_ajax_widget',  // for case owner & user filters in DashboardFeedFilterForm
], function (
    $,
    initialPageData,
    kissmetricsAnalytics,
    utils,
    createModels,
    listModels
) {
    $(function () {
        var $createExport = $("#create-export"),
            isOData = initialPageData.get('is_odata', true),
            isGSheet = initialPageData.get('is_data', true);

        if ($createExport.length) {
            $createExport.koApplyBindings(createModels.createExportModel({
                model_type: initialPageData.get("model_type", true),
                drilldown_fetch_url: initialPageData.reverse('get_app_data_drilldown_values'),
                drilldown_submit_url: initialPageData.reverse('submit_app_data_drilldown_form'),
                page: {
                    is_daily_saved_export: initialPageData.get('is_daily_saved_export', true),
                    is_feed: initialPageData.get('is_feed', true),
                    is_deid: initialPageData.get('is_deid', true),
                    is_odata: isOData,
                    is_gsheet: isGSheet,
                    model_type: initialPageData.get('model_type', true),
                },
            }));
            $('#createExportOptionsModal').on('show.bs.modal', function () {
                kissmetricsAnalytics.track.event("Clicked New Export");

                if (isOData) {
                    kissmetricsAnalytics.track.event("[BI Integration] Clicked + Add Odata Feed button");
                }

                if (isGSheet) {
                    kissmetricsAnalytics.track.event("[BI Integration] Clicked + Add Google Sheet button");
                }

                const exportAction = getExportAction();
                const metricsMessage = `${exportAction} Export - Clicked Add Export Button`;
                kissmetricsAnalytics.track.event(metricsMessage, {
                    domain: initialPageData.get('domain'),
                });
            });
        }

        if (isOData) {
            kissmetricsAnalytics.track.event("[BI Integration] Visited feature page");
            kissmetricsAnalytics.track.outboundLink(
                '#js-odata-track-learn-more',
                "[BI Integration] Clicked Learn More-Wiki"
            );
            kissmetricsAnalytics.track.outboundLink(
                '#js-odata-track-learn-more-preview',
                "[BI Integration] Clicked Learn More-Feature Preview"
            );
        }

        if (isGSheet) {
            kissmetricsAnalytics.track.event("[BI Integration] Visited feature page");
            kissmetricsAnalytics.track.outboundLink(
                '#js-gsheet-track-learn-more',
                "[BI Integration] Clicked Learn More-Wiki"
            );
            kissmetricsAnalytics.track.outboundLink(
                '#js-gsheet-track-learn-more-preview',
                "[BI Integration] Clicked Learn More-Feature Preview"
            );
        }

        var modelType = initialPageData.get("model_type");
        $("#export-list").koApplyBindings(listModels.exportListModel({
            modelType: modelType,
            isDeid: initialPageData.get('is_deid'),
            isDailySavedExport: initialPageData.get('is_daily_saved_export', true),
            isFeed: initialPageData.get('is_feed', true),
            isOData: isOData,
            isGSheet: isGSheet,
            headers: {
                my_export_type: initialPageData.get('my_export_type'),
                shared_export_type: initialPageData.get('shared_export_type'),
                export_type_caps_plural: initialPageData.get('export_type_caps_plural'),
            },
            urls: {
                commitFilters: initialPageData.reverse("commit_filters"),
                getExportsPage: initialPageData.reverse("get_exports_page"),
                poll: initialPageData.reverse("get_saved_export_progress"),
                toggleEnabled: initialPageData.reverse("toggle_saved_export_enabled"),
                update: initialPageData.reverse("update_emailed_export_data"),
            },
        }));

        if (modelType === 'form') {
            kissmetricsAnalytics.track.event('Visited Export Forms Page');
        } else if (modelType === 'case') {
            kissmetricsAnalytics.track.event('Visited Export Cases Page');
        }

        // Analytics: Send Kissmetrics event when user closes alert bubble
        $('#alert-export-deep-links').on('click', function () {
            kissmetricsAnalytics.track.event("Dismissed alert bubble - Deep links in exports");
        });
    });

    function getExportAction() {
        const modelType = initialPageData.get('model_type', true);
        if (modelType) {
            return utils.capitalize(modelType);
        }

        const isDailySavedExport = initialPageData.get('is_daily_saved_export', true);
        const isExcelExport = initialPageData.get('is_feed', true);
        const isOData = initialPageData.get('is_odata', true);
        const isGSheet = initialPageData.get('is_gsheet', true);

        if (isDailySavedExport) {
            // NOTE: Currently, excel exports are considered daily exports,
            // but if this was not intentional, this code should be separated
            return (isExcelExport ? 'Excel Dashboard' : 'Daily Saved');
        } else if (isOData) {
            return 'PowerBI';
        }
    }
});
