document.addEventListener("DOMContentLoaded", () => {
  const messagesBox = document.getElementById("messages");

  if (messagesBox) {
    // Прокрутка вниз
    messagesBox.scrollTop = messagesBox.scrollHeight;

    // Анимация сообщений
    const msgs = messagesBox.querySelectorAll(".message");
    msgs.forEach((msg, i) => {
      msg.style.opacity = 0;
      msg.style.transform = "translateY(10px)";
      setTimeout(() => {
        msg.style.transition = "all 0.4s ease";
        msg.style.opacity = 1;
        msg.style.transform = "translateY(0)";
      }, i * 40);
    });
  }
});
