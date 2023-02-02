 jQuery(document).ready(function(){
   jQuery('ul li a').click(function(){
     jQuery('li a').removeClass("active");
     jQuery(this).addClass("active");
});
});

