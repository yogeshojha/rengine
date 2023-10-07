from django.urls import include, path

from . import views

urlpatterns = [
    path(
        '',
        views.index,
        name='targetIndex'),
    path(
        '<slug:slug>/add/target',
        views.add_target,
        name='add_target'),
    path(
        '<slug:slug>/add/organization',
        views.add_organization,
        name='add_organization'),
    path(
        '<slug:slug>/update/target/<int:id>',
        views.update_target,
        name='update_target'),
    path(
        '<slug:slug>/update/organization/<int:id>',
        views.update_organization,
        name='update_organization'),
    path(
        '<slug:slug>/list/target',
        views.list_target,
        name='list_target'),
    path(
        '<slug:slug>/list/organization',
        views.list_organization,
        name='list_organization'),
    path(
        'delete/target/<int:id>',
        views.delete_target,
        name='delete_target'),
    path(
        'delete/organization/<int:id>',
        views.delete_organization,
        name='delete_organization'),
    path(
        '<slug:slug>/delete/multiple',
        views.delete_targets,
        name='delete_multiple_targets'),
    path(
        '<slug:slug>/summary/<int:id>',
        views.target_summary,
        name='target_summary'),
]
