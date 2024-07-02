from django.db import models
from django.utils import timezone
from jsonfield import JSONField

class Organization(models.Model):
    organization = models.CharField(max_length=255, verbose_name="Организация")
    is_general_contractor = models.BooleanField(default=False, verbose_name="Генеральный подрядчик")

    def __str__(self):
        return self.organization

    class Meta:
        verbose_name = "Организация"
        verbose_name_plural = "Организации"

class User(models.Model):
    chat_id = models.CharField(max_length=100, unique=True, verbose_name="Chat ID")
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    is_authorized = models.BooleanField(default=False, verbose_name="Авторизован")
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Организация")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

class WorkType(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Вид работ")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Вид работ"
        verbose_name_plural = "Виды работ"

class Object(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название объекта")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Объект"
        verbose_name_plural = "Объекты"

class BlockSection(models.Model):
    object = models.ForeignKey(Object, on_delete=models.CASCADE, related_name='block_sections', verbose_name="Объект")
    name = models.CharField(max_length=255, unique=True, verbose_name="Блок/Секция")
    number_of_floors = models.IntegerField(verbose_name="Количество этажей")

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = "Блок/Секция"
        verbose_name_plural = "Блоки/Секции"


class FrontTransfer(models.Model):
    STATUS_CHOICES = [
        ('transferred', 'Передано'),
        ('approved', 'Одобрено'),
        ('with_remarks', 'Есть замечания'),
        ('on_consideration', 'На рассмотрении'),
        ('deleted', 'Удалено из-за ошибки'),
        ('in_process', 'В процессе выполнения')
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_transfers', verbose_name="Отправитель")
    object = models.ForeignKey(Object, on_delete=models.CASCADE, verbose_name="Объект")
    work_type = models.ForeignKey(WorkType, on_delete=models.CASCADE, verbose_name="Вид работы")
    block_section = models.ForeignKey(BlockSection, on_delete=models.CASCADE, verbose_name="Блок/Секция")
    floor = models.CharField(verbose_name="Этаж", max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Статус")
    photo1 = models.ImageField(upload_to='photos/', null=True, blank=True, verbose_name="Фото 1")
    photo2 = models.ImageField(upload_to='photos/', null=True, blank=True, verbose_name="Фото 2")
    photo3 = models.ImageField(upload_to='photos/', null=True, blank=True, verbose_name="Фото 3")
    photo4 = models.ImageField(upload_to='photos/', null=True, blank=True, verbose_name="Фото 4")
    photo5 = models.ImageField(upload_to='photos/', null=True, blank=True, verbose_name="Фото 5")
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transfers', verbose_name="Получатель")
    remarks = models.TextField(null=True, blank=True, verbose_name="Замечания")
    next_work_type = models.ForeignKey(WorkType, on_delete=models.SET_NULL, null=True, blank=True, related_name='next_transfers', verbose_name="Следующий вид работы")
    boss = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='boss_transfers', verbose_name="Генеральный подрядчик")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата передачи", auto_now_add=False)

    approval_at = models.DateTimeField(default=timezone.now, verbose_name="Дата принятия", auto_now_add=False, null=True, blank=True,)


    photo_ids = JSONField(default=list, verbose_name="ID фотографий", null=True, blank=True)
    sender_chat_id = models.CharField(max_length=100, verbose_name="Chat ID отправителя")

    def __str__(self):
        return f'{self.sender.full_name} - {self.object.name} - {self.work_type.name}'

    class Meta:
        verbose_name = "Передача фронта"
        verbose_name_plural = "Передачи фронта"