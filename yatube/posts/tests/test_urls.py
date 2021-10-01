from django.test import TestCase, Client
from http import HTTPStatus

from ..models import Group, Post, User

POST_TEXT = 'Тестовый текст'


class StaticURLTests(TestCase):

    def test_urls(self):
        pages = {
            '/': HTTPStatus.OK,
            '/about/author/': HTTPStatus.OK,
            '/about/tech/': HTTPStatus.OK,
        }

        for url, status in pages.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status)


class TemplateUrlTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='HasNoName')
        self.group = Group.objects.create(title='TestGroup', slug='test-group')
        self.post = Post.objects.create(
            text=POST_TEXT,
            author=self.user,
            group=self.group)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_uses_correct_template(self):
        pages = {
            '/':
                [{'template': 'posts/index.html',
                  'status': HTTPStatus.OK,
                  'client': self.client}],

            '/group/' + self.group.slug + '/':
                [{'template': 'posts/group_list.html',
                  'status': HTTPStatus.OK,
                  'client': self.client}],

            '/profile/' + self.user.username + '/':
                [{'template': 'posts/profile.html',
                  'status': HTTPStatus.OK,
                  'client': self.client}],

            '/posts/' + str(self.post.id) + '/':
                [{'template': 'posts/post_detail.html',
                  'status': HTTPStatus.OK,
                  'client': self.client}],

            '/create':
                [{'template': 'posts/create_post.html',
                  'status': HTTPStatus.OK,
                  'client': self.authorized_client},
                 {'status': HTTPStatus.OK,
                  'client': self.client,
                  'template': 'users/login.html'}],

            '/posts/' + str(self.post.id) + '/edit':
                [{'template': 'posts/create_post.html',
                  'status': HTTPStatus.OK,
                  'client': self.authorized_client},
                 {'status': HTTPStatus.OK,
                  'client': self.client,
                  'template': 'users/login.html'}],

            '/unexisting_page/': [
                {'status': HTTPStatus.NOT_FOUND,
                 'client': self.client}]
        }
        for url, tests in pages.items():
            for test in tests:
                with self.subTest(url=url, test=test):
                    response = test['client'].get(url, follow=True)
                    self.assertEqual(response.status_code, test['status'])
                    if 'template' in test:
                        self.assertTemplateUsed(response, test['template'])
