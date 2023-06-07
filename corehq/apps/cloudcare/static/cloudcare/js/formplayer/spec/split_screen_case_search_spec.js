/* eslint-env mocha sinon */
/* global Backbone */

describe('Split Screen Case Search', function () {
    const API = hqImport("cloudcare/js/formplayer/menus/api"),
        Controller = hqImport('cloudcare/js/formplayer/menus/controller'),
        FakeFormplayer = hqImport("cloudcare/js/formplayer/spec/fake_formplayer"),
        FormplayerFrontend = hqImport('cloudcare/js/formplayer/app'),
        splitScreenCaseListResponse = hqImport('cloudcare/js/formplayer/spec/fixtures/split_screen_case_list'),
        Toggles = hqImport('hqwebapp/js/toggles'),
        Utils = hqImport('cloudcare/js/formplayer/utils/utils');

    const currentUrl = new Utils.CloudcareUrl({appId: 'abc123'}),
        sandbox = sinon.sandbox.create(),
        stubs = {},
        REGIONS = {
            main: 'main',
            sidebar: 'sidebar',
        };

    let getRegion;

    before(function () {
        sandbox.stub(Utils, 'currentUrlToObject').callsFake(function () {
            return currentUrl;
        });

        sandbox.stub(Backbone.history, 'start').callsFake(sandbox.spy());
        sandbox.stub(Backbone.history, 'getFragment').callsFake(function () {
            return JSON.stringify(currentUrl);
        });
        sandbox.stub(API, 'queryFormplayer').callsFake(FakeFormplayer.queryFormplayer);

        stubs.show = sandbox.stub().returns({ render: function () { return; } });
        stubs.empty = sandbox.stub().callsFake(function () { return; });
        FormplayerFrontend.regions = {
            getRegion: function (region) {
                return {
                    region: region,
                    show: stubs.show,
                    empty: stubs.empty,
                };
            },
            addRegions: function () { return; },
        };
        getRegion = sandbox.spy(FormplayerFrontend.regions, 'getRegion');
        stubs.sidebarEnabled = sandbox.stub(Toggles, 'toggleEnabled').withArgs('SPLIT_SCREEN_CASE_SEARCH');
    });

    beforeEach(function () {
        FormplayerFrontend.currentUser.displayOptions.singleAppMode = false;
        stubs.sidebarEnabled.returns(true);
    });

    afterEach(function () {
        sandbox.resetHistory();
    });

    it('should show sidebar when using split screen case search', function () {
        Controller.showMenu(splitScreenCaseListResponse);

        assert.isTrue(getRegion.calledWith(REGIONS.sidebar));
        assert.isTrue(_.some(stubs.show.getCalls(), call => call.thisValue.region === REGIONS.sidebar));
    });

    it('should empty sidebar if in app preview', function () {
        FormplayerFrontend.currentUser.displayOptions.singleAppMode = true;
        Controller.showMenu(splitScreenCaseListResponse);

        assert.isTrue(getRegion.calledWith(REGIONS.sidebar));
        assert.isTrue(_.some(stubs.empty.getCalls(), call => call.thisValue.region === REGIONS.sidebar));
    });

    it('should empty sidebar if response type not entities', function () {
        splitScreenCaseListResponse.type = '';
        Controller.showMenu(splitScreenCaseListResponse);

        assert.isTrue(getRegion.calledWith(REGIONS.sidebar));
        assert.isTrue(_.some(stubs.empty.getCalls(), call => call.thisValue.region === REGIONS.sidebar));
    });

    it('should empty sidebar if no queryResponse present', function () {
        delete splitScreenCaseListResponse.queryResponse;
        Controller.showMenu(splitScreenCaseListResponse);

        assert.isTrue(getRegion.calledWith(REGIONS.sidebar));
        assert.isTrue(_.some(stubs.empty.getCalls(), call => call.thisValue.region === REGIONS.sidebar));
    });

    it('should empty sidebar if feature flag disabled', function () {
        stubs.sidebarEnabled.returns(false);
        Controller.showMenu(splitScreenCaseListResponse);

        assert.isTrue(getRegion.calledWith(REGIONS.sidebar));
        assert.isTrue(_.some(stubs.empty.getCalls(), call => call.thisValue.region === REGIONS.sidebar));
    });

    it('should show case list area in split screen when response type query', function () {
        splitScreenCaseListResponse.type = 'query';
        Controller.showMenu(splitScreenCaseListResponse);

        assert.isTrue(getRegion.calledWith(REGIONS.main));
        assert.isTrue(_.some(stubs.show.getCalls(), call => call.thisValue.region === REGIONS.main));

        assert.isTrue(getRegion.calledWith(REGIONS.sidebar));
        assert.isTrue(_.some(stubs.show.getCalls(), call => call.thisValue.region === REGIONS.sidebar));
    });

    it('should clear sidebar on menu:select', function () {
        const clearSidebar = sandbox.spy(currentUrl, 'clearSidebar');
        FormplayerFrontend.trigger("menu:select", 0);

        assert.isTrue(clearSidebar.calledOnce);
    });
});
