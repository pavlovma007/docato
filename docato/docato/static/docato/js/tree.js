function toggle_comments( span_elem )
{
    var parent_div = span_elem.parentNode.parentNode;
    jQuery(parent_div).find(".comment_children").children().toggle();
}