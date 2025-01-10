//import "source-map-support";
require('source-map-support').install();

import hqMocha from "mocha/js/main";

import "hqwebapp/spec/assert_properties_spec";
import "hqwebapp/spec/bootstrap3/inactivity_spec";
import "hqwebapp/spec/urllib_spec";
import "hqwebapp/spec/bootstrap3/widgets_spec";

$(function () {
    hqMocha.run();
});
