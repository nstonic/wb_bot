from django.views.generic import ListView

from employers.models import Department, Worker


class DepartmentsView(ListView):
    model = Department
    queryset = Department.objects.all()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['current_url'] = self.request.path
        return context


class WorkersView(ListView):
    model = Worker
    queryset = Worker.objects.filter(is_active=True)
