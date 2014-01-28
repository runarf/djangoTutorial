from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from rango.models import Category, Page, UserProfile
from rango.forms import CategoryForm, PageForm
from rango.forms import UserForm, UserProfileForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from datetime import datetime
from rango.bing_search import run_query
from django.shortcuts import redirect
from django.contrib.auth.models import User

def get_category_list ():
    cat_list = Category.objects.all ()

    for cat in cat_list:
        cat.url = encode_url (cat.name)

    return cat_list

def encode_url (category_name_url):
    return category_name_url.replace (' ', '_')

def decode_url (category_name_url):
    return category_name_url.replace('_', ' ')

@login_required
def restricted (request):
    context = RequestContext (request)
    context_dict = {}
    context_dict['cat_list'] = get_category_list ()

    return render_to_response ('rango/restricted.html',
                               context_dict,
                               context)

def about (request):
    context = RequestContext (request)
    context_dict = {}
    context_dict['cat_list'] = get_category_list ()

    if request.session.get ('visits'):
        count = request.session.get ('visits')
    else:
        count = 0

    context_dict['visits'] = count

    return render_to_response('rango/about.html', context_dict, context)

def category (request, category_name_url):
    context = RequestContext (request)

    category_name = decode_url (category_name_url)
    cat_list = get_category_list ()

    context_dict = {'category_name': category_name,
                    'category_name_url': category_name_url,
                    'cat_list': cat_list}
    

    
    try:
        category = Category.objects.get(name=category_name)

        pages = Page.objects.filter (category=category).order_by ('-views')

        context_dict['pages'] = pages

        context_dict['category'] = category

    except Category.DoesNotExist:
        pass

    if request.method == 'POST':
        query = request.POST ['query'].strip()

        if query:
            result_list = run_query (query)
            context_dict['result_list'] = result_list
        
    return render_to_response('rango/category.html', context_dict, context)



def index(request):
    context = RequestContext (request)
    category_list = Category.objects.order_by ('-likes')[:5]
    page_list = Page.objects.order_by ('-views')[:5]
    cat_list = get_category_list ()
    context_dict = {'categories': category_list,
                    'pages': page_list,
                    'cat_list': cat_list}

    for category in category_list:
        category.url = encode_url (category.name)

    for page in page_list:
        page.url = encode_url (page.title)

    response = render_to_response ('rango/index.html', context_dict, context)

    if request.session.get ('last_visit'):
        last_visit_time = request.session.get ('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now () - datetime.strptime (last_visit_time [:-7], "%Y-%m-%d %H:%M:%S")).seconds > 1:
            request.session ['visits'] = visits + 1
            request.session ['last_visit'] = str(datetime.now ())

    else:
        request.session['last_visit'] = str(datetime.now ())
        request.session['visits'] = 1

    return response

@login_required
def add_category (request):
    context = RequestContext (request)
    context_dict = {}
    cat_list = get_category_list ()
    context_dict['cat_list'] = cat_list
    

    if request.method == 'POST':
        form = CategoryForm (request.POST)

        if form.is_valid ():
            form.save (commit=True)

            return index (request)
        else:
            print form.errors
            
    else:
        form = CategoryForm ()

    context_dict['form'] = form
    return render_to_response ('rango/add_category.html', context_dict, context)


@login_required
def add_page (request, category_name_url):
    context = RequestContext (request)
    context_dict = {}
    context_dict['cat_list'] = get_category_list ()
    
    category_name = decode_url (category_name_url)
    if request.method == 'POST':
        
        form = PageForm (request.POST)
        

        if form.is_valid ():
            page = form.save (commit=False)

            try:
                cat = Category.objects.get (name=category_name)
                page.category = cat
            except Category.DoesNotExist:
                return render_to_response ('rango/add_page.html',
                                           context_dict,
                                           context)

            page.views = 0

            page.save ()
            
            return category (request, category_name_url)
        else:
            print form.errors

    else:
        
        form = PageForm ()

    context_dict['category_name_url'] = category_name_url
    context_dict['category_name'] = category_name
    context_dict['form'] = form
    
    return render_to_response ('rango/add_page.html',
                               context_dict,
                               context)

def register (request):
    context = RequestContext (request)

    context_dict = {}
    context_dict['cat_list'] = get_category_list ()
    registered = False

    if request.method == 'POST':

        user_form = UserForm (data=request.POST)
        profile_form = UserProfileForm (data=request.POST)

        if user_form.is_valid () and profile_form.is_valid ():
            user = user_form.save ()

            user.set_password (user.password)
            user.save ()

            profile = profile_form.save (commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            profile.save ()

            registered = True

        else:
            print user_form.errors, profile_form.errors

    else:
        user_form = UserForm ()
        profile_form = UserProfileForm

    context_dict['user_form'] = user_form
    context_dict['profile_form'] = profile_form
    context_dict['registered'] = registered

    return render_to_response ('rango/register.html',
                               context_dict,
                               context)


def user_login (request):
    context = RequestContext (request)
    context_dict = {}
    context_dict['cat_list'] = get_category_list ()

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate (username=username, password=password)

        if user is not None:

            if user.is_active:
                login (request, user)
                return render_to_response('rango/index.html',
                                          context_dict,
                                          context)
                #return HttpResponseRedirect ('/rango/')
            else:
                return HttpResponse ("Your Rango account is disabled.")

        else:
            print "Invalid login details: {0}, {1}".format (username, password)
            return HttpResponse("Invalid login details supplied.")

    else:
        return render_to_response ('rango/login.html',
                                   context_dict,
                                   context)


@login_required
def user_logout (request):
    logout (request)

    return HttpResponseRedirect('/rango/')

def search (request):
    context = RequestContext (request)
    context_dict = {}
    context_dict['cat_list'] = get_category_list ()
    result_list = []

    if request.method == 'POST':
        query = request.POST ['query'].strip()

        if query:
            result_list = run_query (query)

    context_dict['result_list'] = result_list
    return render_to_response ('rango/search.html',
                               context_dict,
                               context)

def profile (request):
    context = RequestContext (request)
    context_dict = {}
    context_dict['cat_list'] = get_category_list ()
    u = User.objects.get (username=request.user)

    try:
        up = UserProfile.objects.get (user=u)
    except:
        up = None

    context_dict ['user'] = u
    context_dict ['userprofile'] = up

    return render_to_response ('rango/profile.html',
                               context_dict,
                               context)
    

def track_url (request):
    context = RequestContext (request)
    page_id = None
    url = '/rango/'

    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            print page_id
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save ()
                url = page.url

            except:
                pass

            
    
    return redirect (url)
