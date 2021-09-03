/* eslint-env mocha */

describe('WebForm', function () {
    var Const = hqImport("cloudcare/js/form_entry/const"),
        UI = hqImport("cloudcare/js/form_entry/form_ui");

    describe('TaskQueue', function () {
        var callCount,
            flag,
            queue = hqImport("cloudcare/js/form_entry/task_queue").TaskQueue(),
            promise1,
            promise2,
            updateFlag = function (newValue, promise) {
                flag = newValue;
                callCount++;
                return promise;
            };

        beforeEach(function () {
            flag = undefined;
            callCount = 0;

            promise1 = new $.Deferred(),
            promise2 = new $.Deferred();
            queue.addTask('updateFlag', updateFlag, ['one', promise1]);
            queue.addTask('updateFlag', updateFlag, ['two', promise2]);
        });

        it('Executes tasks in order', function () {
            // First task should have been executed immediately
            assert.equal(flag, "one");
            assert.equal(callCount, 1);

            // Second task should execute when first one is resolved
            promise1.resolve();
            assert.equal(flag, "two");
            assert.equal(callCount, 2);

            promise2.resolve();
            queue.execute(); // ensure no hard failure when no tasks in queue
        });

        it('Executes task even when previous task failed', function () {
            promise1.reject();
            assert.equal(flag, "two");
            assert.equal(callCount, 2);
            promise2.resolve();
        });

        it('Clears tasks by name', function () {
            assert.equal(queue.queue.length, 1);
            queue.addTask('doSomethingElse', function () {}, []);
            assert.equal(queue.queue.length, 2);
            queue.clearTasks('updateFlag');
            assert.equal(queue.queue.length, 1);
            queue.clearTasks();
            assert.equal(queue.queue.length, 0);
        });
    });

    describe('WebFormSession', function () {
        var server,
            params,
            Utils = hqImport("cloudcare/js/form_entry/utils"),
            WebFormSession = hqImport("cloudcare/js/form_entry/web_form_session").WebFormSession;

        hqImport("hqwebapp/js/initial_page_data").registerUrl(
            "report_formplayer_error",
            "/a/domain/cloudcare/apps/report_formplayer_error"
        );

        beforeEach(function () {
            // Setup HTML
            try {
                affix('input#submit');
                affix('#content');
            } catch (e) {
                // temporarily catch this error while we work out issues running
                // mocha tests with grunt-mocha. this passes fine in browser
            }

            // Setup Params object
            params = {
                form_url: window.location.host,
                onerror: sinon.spy(),
                onload: sinon.spy(),
                onsubmit: sinon.spy(),
                onLoading: sinon.spy(),
                onLoadingComplete: sinon.spy(),
                resourceMap: sinon.spy(),
                session_data: {},
                xform_url: 'http://xform.url/',
                action: 'dummy',
            };

            // Setup fake server
            server = sinon.fakeServer.create();
            server.respondWith(
                'POST',
                new RegExp(params.xform_url + '.*'),
                [
                    200,
                    { 'Content-Type': 'application/json' },
                    '{ "status": "success", "session_id": "my-session" }',
                ]
            );

            // Setup server constants
            window.XFORM_URL = 'dummy';

            // Setup stubs
            $.cookie = sinon.stub();
            sinon.stub(Utils, 'initialRender');
            sinon.stub(UI, 'getIx').callsFake(function () { return 3; });
        });

        afterEach(function () {
            $('#submit').remove();
            try {
                server.restore();
            } catch (e) {
                // temporarily catch these errors while we work on issues with
                // running mocha tests with grunt-mocha. this passes fine in
                // the browser.
            }
            Utils.initialRender.restore();
            UI.getIx.restore();
            $.unsubscribe();
        });

        it('Should queue requests', function () {
            var sess = WebFormSession(params);
            sess.serverRequest({}, sinon.spy(), false);

            sinon.spy(sess.taskQueue, 'execute');

            assert.isFalse(!!$('input#submit').prop('disabled'));
            assert.isFalse(sess.taskQueue.execute.calledOnce);
            server.respond();
            assert.isFalse(!!$('input#submit').prop('disabled'));
            assert.isTrue(sess.taskQueue.execute.calledOnce);
        });

        it('Should only subscribe once', function () {
            var spy = sinon.spy(),
                spy2 = sinon.spy(),
                sess = WebFormSession(params),
                sess2 = WebFormSession(params);

            sinon.stub(sess, 'newRepeat').callsFake(spy);
            sinon.stub(sess2, 'newRepeat').callsFake(spy2);

            $.publish('formplayer.' + Const.NEW_REPEAT, {});
            assert.isFalse(spy.calledOnce);
            assert.isTrue(spy2.calledOnce);
        });

        it('Should block requests', function () {
            var sess = WebFormSession(params);

            // First blocking request
            $.publish('formplayer.' + Const.NEW_REPEAT, {});

            assert.equal(sess.blockingStatus, Const.BLOCK_ALL);

            // Attempt another request
            $.publish('formplayer.' + Const.NEW_REPEAT, {});

            server.respond();

            assert.equal(sess.blockingStatus, Const.BLOCK_NONE);
            // One call to new-repeat
            assert.equal(server.requests.length, 1);
        });

        it('Should not block requests', function () {
            var sess = WebFormSession(params);

            // First blocking request
            $.publish('formplayer.' + Const.ANSWER, { answer: sinon.spy() });

            assert.equal(sess.blockingStatus, Const.BLOCK_SUBMIT);

            // Attempt another request
            $.publish('formplayer.' + Const.ANSWER, { answer: sinon.spy() });

            server.respond();

            assert.equal(sess.blockingStatus, Const.BLOCK_NONE);
            // two calls to answer
            assert.equal(server.requests.length, 2);

        });

        it('Should handle error in callback', function () {
            var sess = WebFormSession(params);

            sess.handleSuccess({}, 'action', sinon.stub().throws());

            assert.isTrue(sess.onerror.calledOnce);
        });

        it('Should handle error in response', function () {
            var sess = WebFormSession(params),
                cb = sinon.stub();

            sess.handleSuccess({ status: 'error' }, 'action', cb);

            assert.isTrue(sess.onerror.calledOnce);
            assert.isFalse(cb.calledOnce);
        });

        it('Should handle failure in ajax call', function () {
            var sess = WebFormSession(params);
            sess.handleFailure({ responseJSON: { message: 'error' } });

            assert.isTrue(sess.onerror.calledOnce);
        });

        it('Should handle timeout error', function () {
            var sess = WebFormSession(params);
            sess.handleFailure({}, 'action', 'timeout');

            assert.isTrue(sess.onerror.calledOnce);
            assert.isTrue(sess.onerror.calledWith({
                human_readable_message: hqImport("cloudcare/js/form_entry/errors").TIMEOUT_ERROR,
                is_html: false,
            }));
        });

        it('Should ensure session id is set', function () {
            var sess = WebFormSession(params);
            sess.loadForm($('div'), 'en');
            assert.equal(sess.session_id, null);

            server.respond();
            assert.equal(sess.session_id, 'my-session');
        });
    });
});
