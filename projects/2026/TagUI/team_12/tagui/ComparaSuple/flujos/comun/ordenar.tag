// El orden acelera la elección; la ficha todavía debe confirmar producto y precio.
js comparasuple_sorted = comparasuple_sort_order() === 'price_asc'; comparasuple_optional_click = true;
if !comparasuple_sorted && typeof comparasuple_adapter.sort_order == 'function'
  js comparasuple_kind = 'sort'; comparasuple_notches = -3; comparasuple_delta = -490;
  tagui comun/ubicar.tag
  if comparasuple_target.visible && !comparasuple_blocked
    js comparasuple_label = 'sort_menu';
    tagui comun/clic.tag
    if comparasuple_clicked
      for opcion_orden from 1 to 10
        tagui comun/avisos.tag
        js comparasuple_locate('price_asc');
        if comparasuple_target.visible || comparasuple_blocked
          break
        wait 0.1
      if comparasuple_target.visible && !comparasuple_blocked
        js comparasuple_label = 'sort_price_asc';
        tagui comun/clic.tag
        if comparasuple_clicked
          for carga_orden from 1 to 40
            js comparasuple_blocked = comparasuple_page_blocked(); comparasuple_sorted = comparasuple_sort_order() === 'price_asc' && comparasuple_url_matches('exact') && comparasuple_page_ready();
            if comparasuple_sorted || comparasuple_blocked
              break
            wait 0.25
  // Si el menú no navegó, dejar libre la página para la búsqueda habitual.
  if !comparasuple_sorted && !comparasuple_blocked
    js comparasuple_locate('price_asc'); comparasuple_sort_menu_open = comparasuple_target.visible;
    if comparasuple_sort_menu_open
      js comparasuple_locate('sort'); comparasuple_label = 'close_sort_menu';
      if comparasuple_target.visible
        tagui comun/clic.tag
js comparasuple_optional_click = false;
