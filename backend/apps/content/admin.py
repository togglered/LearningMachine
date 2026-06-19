from django.contrib import admin

from .models import Question, Section, SectionType, Subject, TaskGroup, Test


class SectionTypeInline(admin.TabularInline[SectionType, Subject]):
    model = SectionType
    extra = 1


class SectionInline(admin.TabularInline[Section, Test]):
    model = Section
    extra = 1


class TaskGroupInline(admin.TabularInline[TaskGroup, Section]):
    model = TaskGroup
    extra = 1


class QuestionInline(admin.StackedInline[Question, TaskGroup]):
    model = Question
    extra = 1


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin[Subject]):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SectionTypeInline]


@admin.register(SectionType)
class SectionTypeAdmin(admin.ModelAdmin[SectionType]):
    list_display = ("name", "subject")
    list_filter = ("subject",)
    search_fields = ("name",)


@admin.register(Test)
class TestAdmin(admin.ModelAdmin[Test]):
    list_display = ("__str__", "subject", "is_published", "time_limit")
    list_filter = ("subject", "is_published")
    inlines = [SectionInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin[Section]):
    list_display = ("__str__", "test", "section_type", "position")
    list_filter = ("test__subject",)
    inlines = [TaskGroupInline]


@admin.register(TaskGroup)
class TaskGroupAdmin(admin.ModelAdmin[TaskGroup]):
    list_display = ("__str__", "section", "position")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin[Question]):
    list_display = ("__str__", "task_group", "kind", "points", "position")
    list_filter = ("kind",)
    search_fields = ("prompt",)
