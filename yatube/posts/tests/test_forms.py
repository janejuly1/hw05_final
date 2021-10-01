import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from ..models import Group, Post, Comment, User

POST_TEXT = 'Тестовый текст'
EDIT_TEXT = 'New Тестовый текст'
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
COMMENT = 'Комментарий от души'


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CreatePostTests(TestCase):
    def setUp(self):
        self.authorized_client = Client()
        self.user = User.objects.create(username='HasNoName')
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(
            title='TestGroup',
            slug='test-group',
            description='test-description')
        self.post = Post.objects.create(
            text=POST_TEXT,
            group=self.group,
            author=self.user,
        )
        self.post_count = Post.objects.count()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает запись Post."""
        form_data = {'text': POST_TEXT}
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.user.username}))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), self.post_count + 1)
        post = Post.objects.all().order_by('-id')[0]
        self.assertIsNotNone(post)
        self.assertEqual(post.text, POST_TEXT)

    def test_create_post_with_group(self):
        """Валидная форма создает запись Post."""
        form_data = {
            'text': POST_TEXT,
            'group': self.group.id}
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.user.username}))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), self.post_count + 1)
        # Проверяем, что создалась запись с заданным слагом
        post = Post.objects.all().order_by('-id')[0]
        self.assertIsNotNone(post)
        self.assertEqual(post.group.id, self.group.id)
        self.assertEqual(post.text, POST_TEXT)

    def test_create_post_with_image(self):
        """Валидная форма создает запись Post."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': EDIT_TEXT,
            'image': uploaded}
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.user.username}))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), self.post_count + 1)
        post = Post.objects.all().order_by('-id')[0]
        self.assertIsNotNone(post)
        self.assertEqual(post.text, EDIT_TEXT)
        self.assertEqual(post.image, 'posts/small.gif')

    def test_create_guest_post(self):
        form_data = {'text': POST_TEXT}
        # Отправляем POST-запрос
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'users:login') + '?next=/create/')
        self.assertEqual(Post.objects.count(), self.post_count)

    def test_edit_post(self):
        form_data = {'text': EDIT_TEXT}
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True)

        self.post.refresh_from_db()
        self.assertEquals(EDIT_TEXT, self.post.text)

    def test_guest_edit_post(self):
        form_data = {'text': EDIT_TEXT}
        response = self.client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True)

        self.post.refresh_from_db()
        self.assertEquals(POST_TEXT, self.post.text)

        self.assertRedirects(
            response,
            reverse('users:login') + '?next=/posts/1/edit/')


class CommentTests(TestCase):
    def setUp(self):
        self.authorized_client = Client()
        self.user = User.objects.create(username='HasNoName')
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            text=POST_TEXT,
            author=self.user,
        )
        self.comment_count = Comment.objects.count()

    def test_authorized_comment(self):
        form_data = {'text': COMMENT}
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}))

        self.post.refresh_from_db()
        comment = self.post.comments.order_by('-id')[0]
        self.assertEquals(COMMENT, comment.text)
        self.assertEqual(Comment.objects.count(), self.comment_count + 1)
