$(function(){
    var car_m_2 = $('#car_m_2').data('carousel');
    var thumbs = $('#car_m_2_thumbs > .thumb');
    $.each(thumbs, function(){
        var thumb = $(this),  index = thumb.data('index') - 1;
        thumb.on('click', function(){
            car_m_2.slideTo(index);
        });
    });
});