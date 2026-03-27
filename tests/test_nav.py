import re

def test_ingresos_navigation_structure():
    """Verify that the sidebar has a single 'Ingresos' group with both
    'Nuevo ingreso' and 'Historial' as submenu entries, and that there is
    no standalone 'Nuevo ingreso' item outside the group.
    """
    html = open('index.html', 'r', encoding='utf-8').read()

    # ensure the main "Nuevo ingreso" link was moved inside the ingresos group
    assert re.search(r'<div[^>]*class="ni"[^>]*data-p="nuevo-ingreso"', html) is None, \
        "Standalone 'Nuevo ingreso' item should not exist in the top nav"

    # ensure there is exactly one ingresos group
    groups = re.findall(r'data-group="ingresos"', html)
    assert len(groups) == 1, "There should be exactly one ingresos group element"

    # submenu items
    assert re.search(r'<div[^>]*class="sni"[^>]*data-p="nuevo-ingreso"', html), \
        "Nuevo ingreso submenu item must exist"
    assert re.search(r'<div[^>]*class="sni"[^>]*data-p="ingresos"', html), \
        "Historial submenu item must exist"

    # clicking on the parent should call go('ingresos')
    assert "go('ingresos')" in html.split('data-group="ingresos"')[1], \
        "Clicking the ingresos parent should navigate to historial (ingresos)"
