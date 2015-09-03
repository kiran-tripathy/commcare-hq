(function (angular, undefined) {
    'use strict';
    // module: hq.download_export

    /* This is the helper module for the Download Exports Page. */

    var download_export = angular.module('hq.download_export', [
        'ngResource',
        'ngRoute',
        'ng.django.rmi',
        'ngMessages'
    ]);

    var $element = {
        progress: function () {
            return $('#download-progress-bar');
        },
        group: function () {
            return $('#id_group');
        },
        user_type: function () {
            return $('#id_user_types');
        }
    };

    download_export.constant('exportList', []);

    var exportsControllers = {};
    exportsControllers.DownloadExportFormController = function (
        $scope, djangoRMI, exportList, exportDownloadService
    ) {
        var self = {};
        $scope._ = _;   // make underscore.js available
        $scope.formData = {};
        $scope.exportList = _.map(exportList, function (exportData) {
            exportData['filename'] = encodeURIComponent(exportData['name']);
            return exportData;
        });

        $scope.formData.type_or_group = 'type';
        $scope.formData.user_types = ['mobile'];
        $element.user_type().select2('val', ['mobile']);

        $scope.preparingExport = false;

        $scope.hasGroups = false;
        $scope.groupsLoading = true;
        $scope.groupsError = false;
        self._groupRetries = 0;

        self._handleGroupError = function () {
            $scope.groupsLoading = false;
            $scope.groupsError = true;
        };

        self._handleGroupRetry = function () {
            if (self._groupRetries > 3) {
                self._handleGroupError();
            } else {
                self._groupRetries ++;
                self._getGroups();
            }
        };

        self._updateGroups = function (data) {
            if (data.success) {
                $scope.groupsLoading = false;
                $scope.hasGroups = data.groups.length > 0;
                $element.group().select2({
                    data: data.groups
                });
            } else {
                self._handleGroupRetry();
            }
        };

        self._getGroups = function () {
            djangoRMI.get_group_options({})
                .success(self._updateGroups)
                .error(self._handleGroupRetry);
        };

        self._getGroups();

        $scope.isFormInvalid = function () {
            if ($scope.formData.type_or_group === 'group') {
                return _.isEmpty($scope.formData.group);
            }
            return _.isEmpty($scope.formData.user_types);
        };

        $scope.prepareExport = function () {
            $scope.preparingExport = true;
            djangoRMI.prepare_custom_export({
                exports: $scope.exportList,
                form_data: $scope.formData
            })
                .success(function (data) {
                    if (data.success) {
                        $scope.preparingExport = false;
                        $scope.downloadInProgress = true;
                        exportDownloadService.startDownload(data.download_id);
                    } else {
                        // todo deal with error
                    }
                })
                .error(function () {
                        // todo deal with error
                });
        };

        $scope.$watch(function () {
            return exportDownloadService.showDownloadStatus;
        }, function (status) {
            $scope.downloadInProgress = status;
        });
        $scope.downloadInProgress = false;
    };

    exportsControllers.DownloadProgressController = function (
        $scope, exportDownloadService
    ) {
        var self = {};

        self._reset = function () {
            $scope.showProgress = false;
            $scope.showDownloadStatus = false;
            $scope.isDownloadReady = false;
            $scope.isDownloaded = false;
            $scope.dropboxUrl = null;
            $scope.downloadUrl = null;
            $scope.progress = {};
            $element.progress().css('width', '0%');
            $element.progress().removeClass('progress-bar-success');
        };

        self._reset();

        $scope.$watch(function () {
            return exportDownloadService.downloadStatusData;
        }, function (data) {
            if (!_.isEmpty(data)) {
                $scope.progress = data.progress;
                self._updateProgressBar(data);
                $scope.showProgress = true;
            }
        });

        self._updateProgressBar = function (data) {
            var progressPercent = 0;
            if (data.is_ready && data.has_file) {
                progressPercent = 100;
                $scope.isDownloadReady = true;
                $scope.dropboxUrl = data.dropbox_url;
                $scope.downloadUrl = data.download_url;
                $element.progress().addClass('progress-bar-success');
            } else if (_.isNumber(data.progress.percent)) {
                progressPercent = data.progress.percent;
            }
            $scope.progress.percent = progressPercent;
            $element.progress().css('width', progressPercent + '%');
        };

        $scope.resetDownload = function () {
            self._reset();
            exportDownloadService.resetDownload();
        };

        $scope.$watch(function () {
            return exportDownloadService.showDownloadStatus;
        }, function (status) {
            $scope.showDownloadStatus = status;
        });
    };
    download_export.controller(exportsControllers);

    var downloadExportServices = {};
    downloadExportServices.exportDownloadService = function ($interval, djangoRMI) {
        var self = {};

        self.resetDownload = function () {
            self.downloadId = null;
            self._numErrors = 0;
            self.downloadStatusData = null;
            self.showDownloadStatus = false;
        };

        self.resetDownload();

        self._checkDownloadProgress = function () {
            djangoRMI.poll_custom_export_download({
                download_id: self.downloadId
            })
                .success(function (data) {
                    if (data.is_poll_successful) {
                        self.downloadStatusData = data;
                        if (data.has_file && data.is_ready) {
                            $interval.cancel(self._promise);
                        }
                    } else {
                        self._dealWithErrors();
                    }
                })
                .error(self._dealWithErrors);
        };

        self._dealWithErrors = function () {
            if (self._numErrors > 3) {
                console.log('deal with error');
                $interval.cancel(self._promise);
            }
            self._numErrors ++;
        };

        self.startDownload = function (downloadId) {
            self.showDownloadStatus = true;
            self.downloadId = downloadId;
            self._promise = $interval(self._checkDownloadProgress, 2000);
        };

        return self;
    };
    download_export.factory(downloadExportServices);

}(window.angular));
