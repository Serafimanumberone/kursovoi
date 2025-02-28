// Обработчики событий click
$('.tabs .tab').click(function () {
    if ($(this).hasClass('signin')) {
        $('.tabs .tab').removeClass('active');
        $(this).addClass('active');
        $('.cont').hide();
        $('.signin-cont').show();
    }
    if ($(this).hasClass('signup')) {
        showSignUp(); // Вызываем новую функцию здесь
    }
});

// Функция для отображения формы регистрации
function showSignUp() {
    $('.tabs .tab').removeClass('active');
    $('.signup').addClass('active');
    $('.cont').hide();
    $('.signup-cont').show();
}

// Обработчик события mousemove
$('.container .bg').mousemove(function (e) {
    var amountMovedX = (e.pageX * -1 / 30);
    var amountMovedY = (e.pageY * -1 / 9);
    $(this).css('background-position', amountMovedX + 'px ' + amountMovedY + 'px');
});
