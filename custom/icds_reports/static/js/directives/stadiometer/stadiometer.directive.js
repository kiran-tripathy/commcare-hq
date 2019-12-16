/* global d3 */
var url = hqImport('hqwebapp/js/initial_page_data').reverse;

function StadiometerController($scope, $routeParams, $location, $filter, infrastructureService, locationsService,
    dateHelperService, navigationService, userLocationId, storageService, haveAccessToAllLocations,
    baseControllersService, isAlertActive) {
    baseControllersService.BaseController.call(this, $scope, $routeParams, $location, locationsService,
        dateHelperService, navigationService, userLocationId, storageService, haveAccessToAllLocations);
    var vm = this;
    vm.isAlertActive = isAlertActive;
    if (Object.keys($location.search()).length === 0) {
        $location.search(storageService.getKey('search'));
    } else {
        storageService.setKey('search', $location.search());
    }
    vm.label = "AWCs that reported having a Stadiometer";
    vm.steps = {
        'map': {route: '/awc_infrastructure/stadiometer/map', label: 'Map View'},
        'chart': {route: '/awc_infrastructure/stadiometer/chart', label: 'Chart View'},
    };
    vm.data = {
        legendTitle: 'Percentage',
    };
    vm.filters = ['gender', 'age'];
    vm.rightLegend = {
        info: 'Of the AWCs that have submitted an Infrastructure Details form, the percentage of AWCs that reported having a Stadiometer. ',
    };

    vm.templatePopup = function(loc, row) {
        var total = row ? $filter('indiaNumbers')(row.in_month) : 'N/A';
        var percent = row ? d3.format('.2%')(row.in_month / (row.all || 1)) : "N/A";
        return vm.createTemplatePopup(
            loc.properties.name,
            [{
                indicator_name: 'Number of AWCs that reported having a Stadiometer: ',
                indicator_value: total,
            },
            {
                indicator_name: '% of AWCs that reported having a Stadiometer: ',
                indicator_value: percent,
            }]
        );
    };

    vm.loadData = function () {
        vm.setStepsMapLabel();
        var usePercentage = true;
        var forceYAxisFromZero = false;
        vm.myPromise = infrastructureService.getStadiometerData(vm.step, vm.filtersData).then(
            vm.loadDataFromResponse(usePercentage, forceYAxisFromZero)
        );
    };

    vm.init();

    var options = {
        'xAxisTickFormat': '%b %Y',
        'yAxisTickFormat': ".2%",
        'captionContent': ' Of the AWCs that have submitted an Infrastructure Details form, the percentage of AWCs that reported having a Stadiometer. ',
    };
    vm.chartOptions = vm.getChartOptions(options);
    vm.chartOptions.chart.color = d3.scale.category10().range();

    vm.tooltipContent = function (monthName, dataInMonth) {
        return vm.createTooltipContent(
            monthName,
            [{
                indicator_name: 'Number of AWCs that reported having a Stadiometer: ',
                indicator_value: $filter('indiaNumbers')(dataInMonth.in_month),
            },
            {
                indicator_name: '% of AWCs that reported having a Stadiometer: ',
                indicator_value: d3.format('.2%')(dataInMonth.y),
            }]
        );
    };
}

StadiometerController.$inject = [
    '$scope', '$routeParams', '$location', '$filter',
    'infrastructureService', 'locationsService', 'dateHelperService', 'navigationService', 'userLocationId',
    'storageService', 'haveAccessToAllLocations', 'baseControllersService', 'isAlertActive'
];

window.angular.module('icdsApp').directive('stadiometer', function() {
    return {
        restrict: 'E',
        templateUrl: url('icds-ng-template', 'map-chart'),
        bindToController: true,
        scope: {
            data: '=',
        },
        controller: StadiometerController,
        controllerAs: '$ctrl',
    };
});
