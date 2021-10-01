from django.test import TestCase

from ..models import Post, Group, User


class ModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='HasNoName')
        self.group = Group.objects.create(
            title='TestGroup',
            slug='test-group',
            description='test-description')
        self.post = Post.objects.create(
            text='очень очень длинный текст'
            'очень очень длинный текст очень'
            'очень длинный текст очень очень длинный текст',
            group=self.group,
            author=self.user,)

    def test_group(self):
        """__str__  task - это строчка с содержимым group.title."""
        self.assertEqual(str(self.group), self.group.title)

    def test_post(self):
        self.assertEqual(str(self.post), self.post.text[:15])
        self.assertEqual(
            Post._meta.get_field('text').verbose_name,
            'Текст')
        self.assertEqual(self.post.group.id, self.group.id)
        self.assertEqual(
            Post._meta.get_field('group').verbose_name,
            'Группа')
