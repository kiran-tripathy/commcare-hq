/*global Backbone, Marionette */

hqDefine("cloudcare/js/formplayer/users/views", function () {
    var FormplayerFrontend = hqImport("cloudcare/js/formplayer/app"),
        Util = hqImport("cloudcare/js/formplayer/utils/util");

    /**
     * RestoreAsBanner
     *
     * This View represents the banner that indicates what user your are
     * currently logged in (or restoring) as.
     */
    var RestoreAsBanner = Marionette.View.extend({
        template: _.template($("#restore-as-banner-template").html() || ""),
        className: 'restore-as-banner-container',
        ui: {
            clear: '.js-clear-user',
        },
        events: {
            'click @ui.clear': 'onClickClearUser',
        },
        templateContext: function () {
            return {
                restoreAs: this.model.restoreAs,
                username: this.model.getDisplayUsername(),
            };
        },
        onClickClearUser: function () {
            FormplayerFrontend.trigger('clearRestoreAsUser');
        },
    });

    /**
     * UserRowView
     *
     * Represents a single row in the Log In As User list
     */
    var UserRowView = Marionette.View.extend({
        template: _.template($("#user-row-view-template").html() || ""),
        className: 'formplayer-request js-user',
        tagName: 'tr',
        events: {
            'click': 'onClickUser',
        },
        onClickUser: function () {
            Util.confirmationModal({
                title: gettext('Log in as ' + this.model.get('username') + '?'),
                message: _.template($('#user-data-template').html())(
                    { user: this.model.toJSON() }
                ),
                confirmText: gettext('Yes, log in as this user'),
                onConfirm: function () {
                    hqImport("cloudcare/js/formplayer/users/utils").Users.logInAsUser(this.model.get('username'));
                    FormplayerFrontend.trigger('navigateHome');
                    FormplayerFrontend.regions.getRegion('restoreAsBanner').show(
                        new RestoreAsBanner({
                            model: FormplayerFrontend.getChannel().request('currentUser'),
                        })
                    );
                }.bind(this),
            });
        },
    });

    /**
     * RestoreAsView
     *
     * Renders all possible users to log in as. Equipped with pagination
     * and custom querying.
     */
    var RestoreAsView = Marionette.CollectionView.extend({
        childView: UserRowView,
        childViewContainer: 'tbody',
        template: _.template($("#restore-as-view-template").html() || ""),
        limit: 10,
        maxPagesShown: 10,
        initialize: function (options) {
            this.model = new Backbone.Model({
                page: options.page || 1,
                query: options.query || '',
            });
            this.model.on('change', function () {
                this.fetchUsers();
                this.navigate();
            }.bind(this));
            this.fetchUsers();
        },
        ui: {
            search: '.js-user-search',
            query: '.js-user-query',
            page: '.js-page',
            paginationGoButton: '#pagination-go-button',
            paginationGoText: '#goText',
            perPage: '.js-page-limit',
        },
        events: {
            'click @ui.page': 'onClickPage',
            'submit @ui.search': 'onSubmitUserSearch',
            'click @ui.paginationGoButton': 'paginationGoAction',
            'click @ui.perPage': 'onClickPageLimit',
        },
        templateContext: function () {
            var paginateItems = hqImport("cloudcare/js/formplayer/menus/views");
            var paginationOptions = paginateItems.paginateOptions(this.model.get('page') - 1, this.totalPages());
            return {
                total: this.collection.total,
                totalPages: this.totalPages(),
                limit: this.limit,
                rowRange: [10, 25, 50, 100],
                startPage: paginationOptions.startPage,
                endPage: paginationOptions.endPage,
                pageCount: paginationOptions.pageCount,
                currentPage: this.model.get('page') - 1,
                perPageOptionsText: '15 per page',
            };
        },
        navigate: function () {
            FormplayerFrontend.navigate(
                '/restore_as/' +
                this.model.get('page') + '/' +
                this.model.get('query')
            );
        },
        totalPages: function () {
            return Math.ceil(this.collection.total / this.limit);
        },
        fetchUsers: function () {
            this.collection.fetch({
                reset: true,
                data: {
                    query: this.model.get('query'),
                    limit: this.limit,
                    page: this.model.get('page'),
                },
            })
                .done(this.render.bind(this))
                .fail(function (xhr) {
                    FormplayerFrontend.trigger('showError', xhr.responseText);
                });
        },
        onClickPage: function (e) {
            e.preventDefault();
            var page = $(e.currentTarget).data().id;
            this.model.set('page', page + 1);
        },
        onSubmitUserSearch: function (e) {
            e.preventDefault();
            this.model.set({
                'query': this.ui.query.val(),
                'page': 1,  // Reset page to one when doing a query
            });
        },
        paginationGoAction: function (e) {
            var paginateItems = hqImport("cloudcare/js/formplayer/menus/views");
            e.preventDefault();
            var page = Number(this.ui.paginationGoText.val());
            var pageNo = paginateItems.paginationGoPageNumber(page, this.totalPages());
            this.model.set('page', pageNo);
        },
        onClickPageLimit: function (e) {
            e.preventDefault();
            var rowCount = this.ui.perPage.val();
            this.limit = Number(rowCount);
            this.fetchUsers();
            this.model.set('page', 1);
        },
    });

    return {
        RestoreAsBanner: function (options) {
            return new RestoreAsBanner(options);
        },
        RestoreAsView: function (options) {
            return new RestoreAsView(options);
        },
    };
});

