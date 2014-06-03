$(".btn-yes").click(function(e){
    $(this).toggleClass("btn-default btn-success");
});
$(".btn-no").click(function(e){
    $(this).toggleClass("btn-default btn-danger");
});
$(".btn-unsure").click(function(e){
    $(this).toggleClass("btn-default btn-warning");
});
var setupNewSurveyForm = function(data) {
	console.log("got json response");
	samplingdata = data;

	var first_sample = samplingdata;
	var sample_iati_identifier = first_sample["iati-identifier"];
	var elt = $("#data-iati-identifier");
    elt.html(sample_iati_identifier);
    $("#sampling-container")[0].data = first_sample;
};

var getNewData = function() {
	$.getJSON("/api/sampling", function(data) { 
        setupNewSurveyForm(data);
	});
};

$(document).ready(function(){
	var samplingdata;

	getNewData();
});

$("#next-btn").click(function(e) {
    var data = $("#sampling-container")[0].data;
    $.post("/api/sampling/process/", data, function(returndata){
		getNewData();
    });
});

