'use strict';

hqDefine("geospatial/js/geospatial_map", [
    "jquery",
    "hqwebapp/js/initial_page_data",
    "knockout",
    'geospatial/js/models',
    'hqwebapp/js/bootstrap3/alert_user',
    'select2/dist/js/select2.full.min',
], function (
    $,
    initialPageData,
    ko,
    models,
    alertUser
) {
    const caseMarkerColors = {
        'default': "#808080", // Gray
        'selected': "#00FF00", // Green
    };
    const userMarkerColors = {
        'default': "#0e00ff", // Blue
        'selected': "#0b940d", // Dark Green
    };

    const MAP_CONTAINER_ID = 'geospatial-map';

    var saveGeoJSONUrl = initialPageData.reverse('geo_polygon');
    var runDisbursementUrl = initialPageData.reverse('case_disbursement');
    var disbursementRunner;

    var mapModel;
    var polygonFilterModel;

    function showMapControls(state) {
        $("#geospatial-map").toggle(state);
        $("#case-buttons").toggle(state);
        $("#mapControls").toggle(state);
        $("#user-filters-panel").toggle(state);
    }

    var saveGeoJson = function () {
        const data = mapModel.drawControls.getAll();
        if (data.features.length) {
            let name = window.prompt(gettext("Name of the Area"));
            data['name'] = name;

            $.ajax({
                type: 'post',
                url: saveGeoJSONUrl,
                dataType: 'json',
                data: JSON.stringify({'geo_json': data}),
                contentType: "application/json; charset=utf-8",
                success: function (ret) {
                    delete data.name;
                    // delete drawn area
                    mapModel.drawControls.deleteAll();
                    console.log('newPoly', name);
                    polygonFilterModel.savedPolygons.push(
                        new models.SavedPolygon({
                            name: name,
                            id: ret.id,
                            geo_json: data,
                        })
                    );
                    // redraw using mapControlsModelInstance
                    polygonFilterModel.selectedSavedPolygonId(ret.id);
                },
            });
        }
    };

    var disbursementRunnerModel = function () {
        var self = {};

        self.isBusy = ko.observable(false);

        self.disbursementErrorMessage = ko.observable('');
        self.showUnassignedCasesError = ko.observable(false);

        self.setBusy = function (isBusy) {
            self.isBusy(isBusy);
            $("#hq-content *").prop("disabled", isBusy);
            if (isBusy) {
                $("#btnRunDisbursement").addClass('disabled');
            } else {
                $("#btnRunDisbursement").removeClass('disabled');
            }
        };

        self.handleDisbursementResults = function (result) {
            // Clean stale disbursement results
            mapModel.removeDisbursementLayers();

            let groupId = 0;
            Object.keys(result).forEach((userId) => {
                const user = mapModel.userMapItems().find((userModel) => {return userModel.itemId === userId;});
                mapModel.caseGroupsIndex[userId] = {groupId: groupId, item: user};

                let cases = [];
                mapModel.caseMapItems().forEach((caseModel) => {
                    if (result[userId].includes(caseModel.itemId)) {
                        cases.push(caseModel);
                        mapModel.caseGroupsIndex[caseModel.itemId] = {groupId: groupId, item: caseModel};
                    }
                });
                connectUserWithCasesOnMap(user, cases);
                groupId += 1;
            });
            self.setBusy(false);
        };

        self.runCaseDisbursementAlgorithm = function (cases, users) {
            self.setBusy(true);
            let mapInstance = mapModel.mapInstance;

            let caseData = [];
            cases.forEach(function (c) {
                const layerId = mapModel.getLineFeatureId(c.itemId);
                if (mapInstance.getLayer(layerId)) {
                    mapInstance.removeLayer(layerId);
                }
                if (mapInstance.getSource(layerId)) {
                    mapInstance.removeSource(layerId);
                }

                caseData.push({
                    id: c.itemId,
                    lon: c.itemData.coordinates.lng,
                    lat: c.itemData.coordinates.lat,
                });
            });

            let userData = users.map(function (c) {
                return {
                    id: c.itemId,
                    lon: c.itemData.coordinates.lng,
                    lat: c.itemData.coordinates.lat,
                };
            });

            $.ajax({
                type: 'post',
                url: runDisbursementUrl,
                dataType: 'json',
                data: JSON.stringify({'users': userData, "cases": caseData}),
                contentType: "application/json; charset=utf-8",
                success: function (ret) {
                    if (ret['unassigned'].length) {
                        self.showUnassignedCasesError(true);
                    }
                    if (ret['assignments']) {
                        self.handleDisbursementResults(ret['assignments']);
                    } else {
                        self.setBusy(false);
                    }
                },
                error: function () {
                    alertUser.alert_user(
                        gettext("Oops! Something went wrong! Please check that your geospatial settings are configured correctly or contact admin if the problem persists."), 'danger'
                    );
                    self.setBusy(false);
                },
            });
        };

        function connectUserWithCasesOnMap(user, cases) {
            cases.forEach((caseModel) => {
                const lineCoordinates = [
                    [user.itemData.coordinates.lng, user.itemData.coordinates.lat],
                    [caseModel.itemData.coordinates.lng, caseModel.itemData.coordinates.lat],
                ];
                let mapInstance = mapModel.mapInstance;
                mapInstance.addLayer({
                    id: mapModel.getLineFeatureId(caseModel.itemId),
                    type: 'line',
                    source: {
                        type: 'geojson',
                        data: {
                            type: 'Feature',
                            properties: {},
                            geometry: {
                                type: 'LineString',
                                coordinates: lineCoordinates,
                            },
                        },
                    },
                    layout: {
                        'line-join': 'round',
                        'line-cap': 'round',
                    },
                    paint: {
                        'line-color': '#808080',
                        'line-width': 1,
                    },
                });
            });
        }

        return self;
    };

    function initMap() {
        mapModel = new models.Map(false, true);
        mapModel.initMap(MAP_CONTAINER_ID);

        let selectedCases = ko.computed(function () {
            return mapModel.caseMapItems().filter(function (currCase) {
                return currCase.isSelected();
            });
        });
        let selectedUsers = ko.computed(function () {
            return mapModel.userMapItems().filter(function (currUser) {
                return currUser.isSelected();
            });
        });

        ko.applyBindings({'userModels': mapModel.userMapItems, 'selectedUsers': selectedUsers}, $("#user-modals")[0]);
        ko.applyBindings({'caseModels': mapModel.caseMapItems, 'selectedCases': selectedCases}, $("#case-modals")[0]);

        mapModel.mapInstance.on("draw.update", selectMapItemsInPolygons);
        mapModel.mapInstance.on('draw.selectionchange', selectMapItemsInPolygons);
        mapModel.mapInstance.on('draw.delete', function () {
            polygonFilterModel.btnSaveDisabled(!mapModel.mapHasPolygons());
            selectMapItemsInPolygons();
        });
        mapModel.mapInstance.on('draw.create', function () {
            polygonFilterModel.btnSaveDisabled(!mapModel.mapHasPolygons());
        });
    }

    function selectMapItemsInPolygons() {
        let features = mapModel.drawControls.getAll().features;
        if (polygonFilterModel.activeSavedPolygon) {
            features = features.concat(polygonFilterModel.activeSavedPolygon.geoJson.features);
        }
        mapModel.selectAllMapItems(features);
    }

    function initPolygonFilters() {
        // Assumes `map` var is initialized
        const $mapControlDiv = $("#mapControls");
        polygonFilterModel = new models.PolygonFilter(mapModel, false, true);
        polygonFilterModel.loadPolygons(initialPageData.get('saved_polygons'));
        if ($mapControlDiv.length) {
            ko.cleanNode($mapControlDiv[0]);
            $mapControlDiv.koApplyBindings(polygonFilterModel);
        }

        const $saveDrawnArea = $("#btnSaveDrawnArea");
        $saveDrawnArea.click(function () {
            if (mapModel && mapModel.mapInstance) {
                saveGeoJson();
            }
        });

        var $exportDrawnArea = $("#btnExportDrawnArea");
        $exportDrawnArea.click(function () {
            if (mapModel && mapModel.mapInstance) {
                polygonFilterModel.exportGeoJson("btnExportDrawnArea");
            }
        });

        var $runDisbursement = $("#btnRunDisbursement");
        $runDisbursement.click(function () {
            $('#disbursement-clear-message').hide();
            if (mapModel && mapModel.mapInstance && !polygonFilterModel.btnRunDisbursementDisabled()) {
                let selectedCases = mapModel.caseMapItems();
                let selectedUsers = mapModel.userMapItems();
                if (mapModel.mapHasPolygons() || polygonFilterModel.activeSavedPolygon) {
                    selectedCases = mapModel.caseMapItems().filter(function (caseItem) {
                        return caseItem.isSelected();
                    });
                    selectedUsers = mapModel.userMapItems().filter((userItem) => {
                        return userItem.isSelected();
                    });
                }

                // User might do polygon filtering on an area with no cases/users. We should not do
                // disbursement if this is the case
                const hasValidData = selectedCases.length && selectedUsers.length;
                if (!hasValidData) {
                    const errorMessage = gettext("Please ensure that the filtered area includes both cases" +
                                                 "and mobile workers before attempting to run disbursement.");
                    disbursementRunner.disbursementErrorMessage(errorMessage);
                } else {
                    disbursementRunner.disbursementErrorMessage('');
                    disbursementRunner.showUnassignedCasesError(false);
                }
                if (hasValidData) {
                    disbursementRunner.runCaseDisbursementAlgorithm(selectedCases, selectedUsers);
                }
            }
        });
    }

    var userFiltersModel = function () {
        var self = {};

        self.shouldShowUsers = ko.observable(false);
        self.hasFiltersChanged = ko.observable(false);  // Used to disable "Apply" button
        self.showFilterMenu = ko.observable(true);
        self.hasErrors = ko.observable(false);
        self.selectedLocation = null;

        self.loadUsers = function () {
            mapModel.removeMarkersFromMap(mapModel.userMapItems());
            mapModel.userMapItems([]);
            self.hasErrors(false);
            if (!self.shouldShowUsers()) {
                self.hasFiltersChanged(false);
                return;
            }

            $.ajax({
                method: 'GET',
                data: {'location_id': self.selectedLocation},
                url: initialPageData.reverse('get_users_with_gps'),
                success: function (data) {
                    self.hasFiltersChanged(false);
                    const userData = _.object(_.map(data.user_data, function (userData) {
                        const gpsData = (userData.gps_point) ? userData.gps_point.split(' ') : [];
                        const lat = parseFloat(gpsData[0]);
                        const lng = parseFloat(gpsData[1]);

                        const editUrl = initialPageData.reverse('edit_commcare_user', userData.id);
                        const link = `<a class="ajax_dialog" href="${editUrl}" target="_blank">${userData.username}</a>`;

                        return [userData.id, {'coordinates': {'lat': lat, 'lng': lng}, 'link': link, 'type': 'user'}];
                    }));

                    const userMapItems = mapModel.addMarkersToMap(userData, userMarkerColors);
                    mapModel.userMapItems(userMapItems);
                },
                error: function () {
                    self.hasErrors(true);
                },
            });
        };

        self.onLocationFilterChange = function (_, e) {
            self.selectedLocation = $(e.currentTarget).select2('val');
            self.onFiltersChange();
        };

        self.onFiltersChange = function () {
            self.hasFiltersChanged(true);
        };

        self.toggleFilterMenu = function () {
            self.showFilterMenu(!self.showFilterMenu());
            const shouldShow = self.showFilterMenu() ? 'show' : 'hide';
            $("#user-filters-panel .panel-body").collapse(shouldShow);
        };

        return self;
    };

    function initUserFilters() {
        const $userFiltersDiv = $("#user-filters-panel");
        if ($userFiltersDiv.length) {
            const userFiltersInstance = userFiltersModel();
            $userFiltersDiv.koApplyBindings(userFiltersInstance);
            $("#location-filter-select").select2({
                placeholder: gettext('All locations'),
                allowClear: true,
                cache: true,
                ajax: {
                    url: initialPageData.reverse('location_search'),
                    dataType: 'json',
                    processResults: function (data) {
                        return {
                            results: $.map(data.results, function (item) {
                                return {
                                    text: item.text,
                                    id: item.id,
                                };
                            }),
                        };
                    },
                },
            });
        }
    }

    function loadCases(caseData) {
        mapModel.removeMarkersFromMap(mapModel.caseMapItems());
        mapModel.caseMapItems([]);
        var casesWithGPS = caseData.filter(function (item) {
            return item[1] !== null;
        });
        // Index by case_id
        var casesById = _.object(_.map(casesWithGPS, function (item) {
            if (item[1]) {
                return [item[0], {'coordinates': item[1], 'link': item[2], 'type': 'case'}];
            }
        }));
        const caseMapItems = mapModel.addMarkersToMap(casesById, caseMarkerColors);
        mapModel.caseMapItems(caseMapItems);
        mapModel.fitMapBounds(caseMapItems);
    }

    $(document).ajaxComplete(function (event, xhr, settings) {
        // When mobile workers are loaded from the user filtering menu, ajaxComplete will be called again.
        // We don't want to reload the map or cases when this happens, so simply return.
        const isAfterUserLoad = settings.url.includes('geospatial/get_users_with_gps/');
        if (isAfterUserLoad) {
            return;
        }

        const isAfterReportLoad = settings.url.includes('geospatial/async/case_management_map/');
        // This indicates clicking Apply button or initial page load
        if (isAfterReportLoad) {
            initMap();
            initPolygonFilters();
            initUserFilters();
            // Hide controls until data is displayed
            showMapControls(false);

            disbursementRunner = new disbursementRunnerModel();
            $("#disbursement-spinner").koApplyBindings(disbursementRunner);
            $("#disbursement-error").koApplyBindings(disbursementRunner);

            return;
        }

        // This indicates that report data is fetched either after apply or after pagination
        const isAfterDataLoad = settings.url.includes('geospatial/json/case_management_map/');
        if (!isAfterDataLoad) {
            return;
        }

        showMapControls(true);
        // Hide the datatable rows but not the pagination bar
        $('.dataTables_scroll').hide();

        if (xhr.responseJSON.aaData.length && mapModel.mapInstance) {
            loadCases(xhr.responseJSON.aaData);
        }
    });
});
