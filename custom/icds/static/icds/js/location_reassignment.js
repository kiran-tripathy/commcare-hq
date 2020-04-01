hqDefine("icds/js/location_reassignment", [
    'jquery',
    'knockout',
    'hqwebapp/js/assert_properties',
    'locations/js/search',
], function (
    $,
    ko,
    assertProperties
) {
    $(function () {
        var LocationReassignmentModel = function (options) {
            assertProperties.assertRequired(options, ['baseUrl']);

            var self = {};
            self.baseUrl = options.baseUrl;

            // Download
            self.location_id = ko.observable('');
            self.url = ko.computed(function () {
                return self.baseUrl + "?location_id=" + (self.location_id() || '');
            });

            // Upload
            self.file = ko.observable();

            return self;
        };

        var $content = $("#hq-content");
        $content.koApplyBindings(LocationReassignmentModel({
            baseUrl: $content.find("#download_link").attr("href"),
        }));
    });
});
