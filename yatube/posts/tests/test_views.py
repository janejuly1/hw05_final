import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms
from django.core.cache import cache

from ..models import Follow, Group, Post, User

POST_TEXT = 'Тестовый текст'
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class ViewsPagesTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='HasNoName')
        self.group = Group.objects.create(title='TestGroup', slug='test-group')
        self.post = Post.objects.create(
            text=POST_TEXT,
            author=self.user,
            group=self.group)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            'posts/index.html':
                [reverse('posts:index')],
            'posts/group_list.html':
                [reverse(
                    'posts:group_list',
                    kwargs={'slug': self.group.slug})],
            'posts/profile.html':
                [reverse(
                    'posts:profile',
                    kwargs={'username': self.user.username})],
            'posts/post_detail.html':
                [reverse(
                    'posts:post_detail',
                    kwargs={'post_id': self.post.id})],
            'posts/create_post.html':
                [reverse(
                    'posts:post_edit',
                    kwargs={'post_id': self.post.id}),
                 reverse('posts:post_create')],
        }
        for tpl, reverse_names in templates_pages_names.items():
            for reverse_name in reverse_names:
                with self.subTest(tpl=tpl, reverse_name=reverse_name):
                    response = self.authorized_client.get(reverse_name)
                    self.assertTemplateUsed(response, tpl)


class PaginatorViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='HasNoName')
        self.group = Group.objects.create(
            title='TestGroup',
            slug='test-group',
            description='test-description')

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.all_posts = 13
        for self.post in range(self.all_posts):
            self.post = Post.objects.create(
                text=POST_TEXT,
                author=self.user,
                group=self.group)

    def test_first_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))
        # Проверка: количество постов на первой странице равно 10.
        self.assertEqual(
            len(response.context['page_obj']),
            settings.MAX_RECORDS_PER_PAGE)

    def test_second_page_contains_three_records(self):
        # Проверка: на второй странице должно быть три поста.
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']),
            self.all_posts % settings.MAX_RECORDS_PER_PAGE)

    def test_auth_client_page_contains_first_ten_records(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        # Проверка: количество постов на первой странице равно 10.
        self.assertEqual(
            len(response.context['page_obj']),
            settings.MAX_RECORDS_PER_PAGE)

    def test_auth_client_page_contains_three_records(self):
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}) + '?page=2')
        # Проверка: количество постов на первой странице равно 10.
        self.assertEqual(
            len(response.context['page_obj']),
            self.all_posts % settings.MAX_RECORDS_PER_PAGE)

    def test_profile_page_contains_first_ten_records(self):
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}))
        # Проверка: количество постов на первой странице равно 10.
        self.assertEqual(
            len(response.context['page_obj']),
            settings.MAX_RECORDS_PER_PAGE)

    def test_profile_page_contains_three_records(self):
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}) + '?page=2')
        # Проверка: количество постов на первой странице равно 10.
        self.assertEqual(
            len(response.context['page_obj']),
            self.all_posts % settings.MAX_RECORDS_PER_PAGE)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ContextPagesTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='HasNoName')
        self.group = Group.objects.create(
            title='TestGroup',
            slug='test-group',
            description='test-description')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            group=self.group,
            text=POST_TEXT,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_urls_has_image(self):
        """Валидная форма создает запись Post."""
        post = self.create_post_with_image(self.group.id)
        self.assertIsNotNone(post.image)

        urls = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                page_obj = response.context.get('page_obj')
                found = False
                for post_in_page in page_obj:
                    if post_in_page.id != post.id:
                        continue

                    self.assertIsNotNone(post_in_page.image)
                    found = True
                    break

                self.assertTrue(found)

    def test_post_detail_has_image(self):
        """Валидная форма создает запись Post."""
        post = self.create_post_with_image()
        self.assertIsNotNone(post.image)
        response = self.client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': post.id}))
        post_in_page = response.context.get('post')
        self.assertEqual(post, post_in_page)
        self.assertIsNotNone(post_in_page.image)

    def test_post_detail_has_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context.get('post').id, self.post.id)

    def test_edit_post_has_correct_context(self):
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        response = self.authorized_client.get(reverse(
            'posts:post_edit',
            kwargs={'post_id': self.post.id}))

        self.assertEqual(response.context.get('is_edit'), True)
        self.assertEqual(response.context.get('post').id, self.post.id)

        for val, expected in form_fields.items():
            with self.subTest(val=val):
                form_field = response.context.get('form').fields.get(val)
                self.assertIsInstance(form_field, expected)

    def test_create_post_has_correct_context(self):
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        response = self.authorized_client.get(reverse('posts:post_create'))

        self.assertEqual(response.context.get('is_edit'), False)

        for val, expected in form_fields.items():
            with self.subTest(val=val):
                form_field = response.context.get('form').fields.get(val)
                self.assertIsInstance(form_field, expected)

    def create_post_with_image(self, group_id=''):
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
            'text': POST_TEXT,
            'image': uploaded,
            'group': group_id}

        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        return Post.objects.all().order_by('-id')[0]


class GroupPostTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='HasNoName')
        self.group = Group.objects.create(
            title='TestGroup',
            slug='test-group',
            description='test-description')
        self.group2 = Group.objects.create(
            title='TestGroup2',
            slug='test-group-two',
            description='test-description2')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            group=self.group,
            text=POST_TEXT,
        )

    def test_post(self):
        pages = {
            'index': reverse('posts:index'),
            'group_list': reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}),
            'profile': reverse(
                'posts:profile',
                kwargs={'username': self.user.username})
        }

        for page, url in pages.items():
            with self.subTest(page=page):
                response = self.client.get(url)

                page_obj = response.context.get('page_obj')
                self.assertIn(self.post, page_obj)

    def test_post_not_in_group2(self):
        response = self.client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group2.slug}))

        page_obj = response.context.get('page_obj')
        self.assertNotIn(self.post, page_obj)

    def test_index_cache(self):
        delete_post = Post.objects.create(
            text='Какой-то текст, его все равно удалять',
            author=self.user,
            group=self.group,
        )
        response = self.client.get(reverse('posts:index'))
        memorised_content = response.content
        delete_post.delete()
        update_response = self.client.get(reverse('posts:index'))
        new_content = update_response.content
        self.assertEqual(memorised_content, new_content)
        cache.clear()
        clear_response = self.client.get(reverse('posts:index'))
        clear_cache = clear_response.content
        self.assertNotEqual(memorised_content, clear_cache)


class FollowingTests(TestCase):
    def setUp(self):
        self.author = User.objects.create(username='Author')
        self.follower = User.objects.create(username='Follower')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.follower)
        self.post = Post.objects.create(
            author=self.author,
            text=POST_TEXT,
        )

    def test_user_can_follow(self):
        response = self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.author.username}))
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.author.username}))
        self.assertTrue(Follow.objects.filter(
            user=self.follower,
            author=self.author).exists())

    def test_user_can_unfollow(self):
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.author.username}))
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.author.username}))
        self.assertFalse(Follow.objects.filter(
            user=self.follower,
            author=self.author).exists())

    def test_new_record_appears_to_followers(self):
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.authorized_client.get(reverse(
            'posts:follow_index',
            kwargs={'username': self.author.username}))
        page_obj = response.context.get('page_obj')
        self.assertIn(self.post, page_obj)

    def test_new_record_appears_to_followers(self):
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        page_obj = response.context.get('page_obj')
        self.assertIn(self.post, page_obj)

    def test_new_record_not_appears_to_others(self):
        response = self.authorized_client.get(reverse('posts:follow_index'))
        page_obj = response.context.get('page_obj')
        self.assertNotIn(self.post, page_obj)
