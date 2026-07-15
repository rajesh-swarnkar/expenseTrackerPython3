// main.js — students will add JavaScript here as features are built

document.addEventListener('DOMContentLoaded', function () {
    var trigger = document.getElementById('how-it-works-trigger');
    var modal = document.getElementById('how-it-works-modal');
    var closeBtn = document.getElementById('how-it-works-close');
    var video = document.getElementById('how-it-works-video');

    if (!trigger || !modal || !closeBtn || !video) return;

    var videoSrc = 'https://www.youtube.com/embed/dQw4w9WgXcQ';

    function openModal(event) {
        event.preventDefault();
        video.src = videoSrc + '?autoplay=1';
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        modal.hidden = true;
        video.src = '';
        document.body.style.overflow = '';
    }

    trigger.addEventListener('click', openModal);
    closeBtn.addEventListener('click', closeModal);

    modal.addEventListener('click', function (event) {
        if (event.target === modal) closeModal();
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !modal.hidden) closeModal();
    });
});
