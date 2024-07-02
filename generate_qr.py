import qrcode

# URL вашего Telegram-бота и пароль
bot_username = 'BrusnikaFrontBot'
secret_password = 'secret_password'

# Создание URL с паролем
qr_url = f'https://t.me/{bot_username}?start={secret_password}'

# Генерация QR-кода
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(qr_url)
qr.make(fit=True)

# Сохранение QR-кода
img = qr.make_image(fill='black', back_color='white')
img.save('qr_code.png')
