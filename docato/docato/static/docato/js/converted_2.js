var $chunks;

function highlight_selected_chunks( minToken, maxToken, classname ) {

	$chunks.filter('.highlighted').removeClass('highlighted');
	var queries = [];
	for (var tok = minToken; tok <= maxToken; tok++)
		queries.push('.token_' + tok);
	$chunks.filter(queries.join(', ')).addClass( classname );
}

function highlight_whole_comment( label ) {

	var chunks_ids = [];
			
	jQuery(label).siblings('.comment_text').find('.chunk').each( function(index, elem) {
	    chunks_ids.push( $(elem).attr('data-token-id') );
	});
			
	var minToken = Math.min.apply( Math, chunks_ids );
	var maxToken = Math.max.apply( Math, chunks_ids );
			
	highlight_selected_chunks( minToken, maxToken, 'highlighted' );
}

jQuery(document).ready(function ($) {

    window.is_discuss = ( $(".discuss_post").length > 0 );
	window.$prev_comment = null;

	// ******************************* scaling ********************************
	var $container = $('#page-container');
	var $pages = $('.pf');
	var $window = $(window);

	var container_style_tmpl = 'transform: scale(1,!!!); -ms-zoom: 1,!!!; '
		+ '-moz-transform: scale(1,!!!); '
		+ '-moz-transform-origin: 0 0; '
		+ '-o-transform: scale(1,!!!); '
		+ '-o-transform-origin: 0 0; '
		+ '-webkit-transform: scale(1,!!!); '
		+ '-webkit-transform-origin: 0 0;'
		+ 'overflow: visible;';
	var pages_style_tmpl = 'transform: scale(!!!,1); -ms-zoom: !!!,1; '
		+ '-moz-transform: scale(!!!,1); '
		+ '-moz-transform-origin: 0 0; '
		+ '-o-transform: scale(!!!,1); '
		+ '-o-transform-origin: 0 0; '
		+ '-webkit-transform: scale(!!!,1); '
		+ '-webkit-transform-origin: 0 0;'
		+ 'margin: 1px 0px;';

	$('.pc').attr('style', 'display: block');
	var baseWidth = 1000.0;
	function rescale() {
		// var scale = ($window.width() >= baseWidth) ? ($window.width() / (baseWidth + 10)) : 1;
		var scale = $window.width() / baseWidth;
		$container.attr('style', container_style_tmpl.replace(/!!!/g, scale));
		$pages.attr('style', pages_style_tmpl.replace(/!!!/g, scale));
	}
	$window.resize(rescale);
	rescale();
	
	// **************************** highlighting ******************************
	var shiftPressed = false;
	$('body').keydown(function (event) {
		if (event.which == 16 || event.shiftKey)
			shiftPressed = true;
	}).keyup(function (event) {
		if (event.which == 16 || event.shiftKey)
			shiftPressed = false;
	});

	$chunks = $('.chunk');
	var lastTokenId = null;

	$chunks.click(function () {
		var self = $(this);
		
		var $parent = self.parent();
		if ( $parent.hasClass('highlight_label') ) {
            highlight_whole_comment( $parent.get(0) );
		    return false;
		}

		var tokenId = self.attr('data-token-id');
	    if (shiftPressed) {
			if (lastTokenId) {
				window.getSelection().collapse($('body')[0], 0);
				var minToken = Math.min(lastTokenId, tokenId);
				var maxToken = Math.max(lastTokenId, tokenId);
				highlight_selected_chunks( minToken, maxToken, 'highlighted' );
			}
		} else {
			$chunks.filter('.highlighted, .token_' + tokenId).toggleClass('highlighted');
			lastTokenId = self.hasClass('highlighted') ? tokenId : null;
		}
	});
	
	function highlight_onmessage( arr, ind )
	{
		var target_elem = $(arr[ind]);

	  	$('html, body').animate({ scrollTop: (target_elem.offset().top - 10)+ 'px' }, 400).promise().done(function () {
    		var cnt = 0, timer_id = null;
    		
    		function toggleAlert() {
    			clearTimeout(timer_id);
    			target_elem.toggleClass('alert');
    			cnt++;
    			if (cnt < 6)
    				timer_id = setTimeout(toggleAlert, 200);
    			else {
					ind++;
					if ( ind < arr.length )
						highlight_onmessage( arr, ind );
    			}
    		}
    			
    		toggleAlert();
    	});
	}
	
	$window.on("message", function(e) {
	    var data = JSON.parse( e.originalEvent.data );
		var arr = data.s_objs.split(';');

        if ( data.command == 'highlight' )
		    highlight_onmessage( arr, 0 );
		else if ( data.command == 'add' ) {
		    for ( var i in arr ) {
	            $chunks.filter('.highlighted').removeClass('highlighted');
                $chunks.filter(arr[i]).each( function() {
                    var $self = $(this);
                    $self.addClass( 'selected' );
                    $self.attr('title', data.fr_name);
                });

		    }
		}
		else if ( data.command == 'delete' ) {
		    for ( var i in arr ) {
                $chunks.filter(arr[i]).each( function() {
                    var $self = $(this);
                    $self.removeClass( 'selected' );
                    this.removeAttribute('title');
                });
		    }
		}
	});
	
	// ****************************** sidebar *********************************
	$('#sidebar').removeClass('opened');

    window.parent.postMessage('markup', '*');

});