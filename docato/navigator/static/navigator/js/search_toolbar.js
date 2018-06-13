jQuery(document).ready(function () {

var search_buttons = $('.navigator .search_button');

function do_search(base_url, query) {
	if (query.length > 0)
		top.frames['browserFrame'].location = base_url + '/' + query;
}

function get_query() {
	return $('.navigator #search_query').val();
}

search_buttons.click(function () {
	do_search($(this).attr('data-search-base-url'), get_query());
});

$('.navigator #add_doc').click(function () {
	add_doc_dialog.dialog('open');
});

});