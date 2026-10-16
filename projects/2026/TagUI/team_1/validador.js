// ==============================================================================
// UTN FRCU - Tecnologías para la Automatización (Año 2026)
// validador.js - Motor de Validación Estricta y Detección de Intención
// ==============================================================================

const catalogo = require('./catalogo.js');

// Normaliza texto: minúsculas, sin diacríticos, espacios limpios
function normalizar(texto) {
    if (!texto || typeof texto !== 'string') return '';
    return texto
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '') // elimina tildes
        .replace(/(\d+)\s*%/g, '$1%')    // normaliza "3 %" a "3%"
        .replace(/[\.,;:!¡?¿\(\)\[\]"'\-_/]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

// Lista de marcas comunes reconocidas en supermercados argentinos
const MARCAS_CONOCIDAS = [
    // Bebidas y Gaseosas / Cervezas
    'coca cola', 'coca-cola', 'coca', 'pepsi', 'fanta', 'sprite', 'manaos',
    '7up', 'seven up', 'aquarius', 'levite', 'villavicencio', 'eco de los andes',
    'kin', 'ivess', 'pritty', 'terma', 'quilmes', 'brahma', 'stella artois',
    'heineken', 'corona', 'andes origen', 'andes', 'patagonia', 'imperial', 'schneider',
    'isenbeck', 'budweiser', 'gancia', 'fernet branca', 'branca', 'campari', 'cinzano',
    'ser', 'cepita', 'tang', 'clight', 'baggio', 'ades', 'bicitrico',
    // Lácteos y Bebidas Lácteas
    'la serenisima', 'serenisima', 'sancor', 'tregar', 'las tres ninas', 'tres ninas',
    'ilolay', 'veronica', 'milkaut', 'manfrey', 'danette', 'danonino', 'actacol',
    'barraza', 'la suipachense', 'suipachense', 'vacalin', 'san ignacio', 'la paulina',
    'casancrem', 'mendicrim', 'tholem', 'cremon',
    // Almacén / Infusiones / Pastas / Granos / Aceites
    'playadito', 'taragui', 'amanda', 'chamigo', 'nobleza gaucha', 'la merced',
    'cruz de malta', 'union', 'cbse', 'rosamonte', 'mananita', 'canuelas', 'natura',
    'cocinero', 'marolio', 'lira', 'pureza', 'blancaflor', 'favorita', 'morixe',
    'lucchetti', 'luchetti', 'matarazzo', 'barilla', 'don vicente', 'knorr', 'maggi',
    'arcor', 'gallo oro', 'gallo', 'molinos ala', 'ala', 'maximo', 'dos hermanos',
    'ledesma', 'chango', 'nescafe', 'dolca', 'arlistan', 'la virginia', 'cabrales',
    'hellmanns', 'danica', 'fanacoa', 'la campagnola', 'salsati', 'maruchan',
    'carrefour', 'coto', 'dia', 'menoyo', 'dos anclas', 'celusal', 'noel',
    // Galletitas / Snacks / Golosinas / Panificados
    'oreo', 'pepitos', 'chocolinas', 'terrabusi', 'sonrisas', 'rumba', 'melba',
    'amor', 'don satur', '9 de oro', 'criollitas', 'express', 'club social', 'traviata',
    'cereal mix', 'lays', 'doritos', 'cheetos', 'guaymallen', 'havanna', 'jorgito',
    'fantoche', 'capitan del espacio', 'bimbo', 'fargo', 'lactal',
    // Higiene y Limpieza
    'dove', 'sedal', 'pantene', 'head & shoulders', 'elvive', 'plusbelle',
    'garnier', 'tresemme', 'colgate', 'oral-b', 'sensodyne', 'aquafresh', 'gillette',
    'rexona', 'axe', 'nivea', 'old spice', 'higienol', 'elegante', 'campanita',
    'felpita', 'scott', 'elite', 'sussex', 'ariel', 'skip', 'drive', 'ala jabon',
    'magistral', 'cif', 'ayudin', 'poett', 'procensol', 'mr musculo', 'blem', 'glade',
    'pampers', 'huggies'
];

// Definición general y exhaustiva de categorías con sus términos válidos e incompatibilidades cruzadas
const DEFINICION_CATEGORIAS = {
    leche: {
        terminos: ['leche', 'lactea', 'descremada', 'entera', 'uht', 'polvo'],
        incompatibles: ['alfajor', 'jugo', 'gaseosa', 'arroz', 'fideos', 'aceite', 'yerba', 'shampoo', 'jabon', 'galletita', 'galleta', 'detergente', 'cerveza', 'vino', 'queso crema', 'dulce de leche', 'bebida vegetal', 'vegetal', 'almendra', 'almendras', 'coco', 'soja', 'avena', 'mani', 'castana', 'castanas']
    },
    yogur: {
        terminos: ['yogur', 'yogurt', 'yogurth'],
        incompatibles: ['leche', 'alfajor', 'arroz', 'fideos', 'shampoo', 'jabon']
    },
    queso: {
        terminos: ['queso', 'cremoso', 'mozzarella', 'muzarella', 'sardo', 'reggianito', 'gouda', 'tybo', 'roquefort', 'brie', 'camembert', 'fontina', 'provolone', 'danbo', 'port salut'],
        incompatibles: ['leche', 'arroz', 'fideos', 'galletita', 'yerba']
    },
    manteca: {
        terminos: ['manteca'],
        incompatibles: ['leche', 'margarina', 'aceite', 'arroz']
    },
    dulce_de_leche: {
        terminos: ['dulce de leche'],
        incompatibles: ['alfajor', 'helado']
    },
    arroz: {
        terminos: ['arroz', 'parboil', 'largo fino', 'doble carolina', 'carnaroli', 'yamani'],
        incompatibles: ['fideos', 'tallarin', 'pasta', 'harina', 'galletita', 'galleta', 'polenta', 'leche', 'aceite', 'yerba', 'alfajor', 'shampoo', 'jabon']
    },
    fideos: {
        terminos: ['fideos', 'fideo', 'tallarin', 'tallarines', 'spaghetti', 'tirabuzon', 'tirabuzones', 'mostachol', 'mostacholes', 'guisero', 'pasta', 'penne', 'rigati', 'fusilli', 'codito', 'moñito', 'sopero', 'cabello de angel'],
        incompatibles: ['arroz', 'harina', 'polenta', 'galletita', 'galleta', 'leche', 'aceite', 'yerba', 'alfajor', 'shampoo']
    },
    harina: {
        terminos: ['harina', '000', '0000', 'leudante'],
        incompatibles: ['arroz', 'fideos', 'azucar', 'polenta']
    },
    polenta: {
        terminos: ['polenta', 'harina de maiz'],
        incompatibles: ['arroz', 'fideos']
    },
    aceite: {
        terminos: ['aceite', 'girasol', 'oliva', 'maiz', 'mezcla'],
        incompatibles: ['vinagre', 'aceto', 'mayonesa', 'arroz', 'fideos', 'leche', 'galletita', 'detergente', 'shampoo']
    },
    vinagre: {
        terminos: ['vinagre', 'aceto'],
        incompatibles: ['aceite', 'arroz', 'leche']
    },
    mayonesa: {
        terminos: ['mayonesa'],
        incompatibles: ['mostaza', 'ketchup', 'aceite', 'leche', 'arroz', 'fideos']
    },
    mostaza: {
        terminos: ['mostaza'],
        incompatibles: ['mayonesa', 'ketchup']
    },
    ketchup: {
        terminos: ['ketchup'],
        incompatibles: ['mayonesa', 'mostaza']
    },
    tomate: {
        terminos: ['pure de tomate', 'tomate triturado', 'pulpa de tomate', 'extracto de tomate', 'salsa de tomate', 'salsa'],
        incompatibles: ['fideos', 'arroz', 'leche']
    },
    yerba: {
        terminos: ['yerba', 'yerba mate', 'mate'],
        incompatibles: ['cafe', 'te', 'mate cocido', 'cacao', 'arroz', 'fideos', 'leche', 'galletita', 'alfajor']
    },
    cafe: {
        terminos: ['cafe', 'torrado', 'tostado', 'molido', 'en grano', 'instantaneo', 'capsulas'],
        incompatibles: ['yerba', 'te', 'mate cocido', 'cacao', 'leche', 'arroz', 'fideos']
    },
    te: {
        terminos: ['te negro', 'te verde', 'te en saquitos', 'te rojo', 'manzanilla', 'boldo', 'tilo'],
        incompatibles: ['yerba', 'cafe', 'arroz']
    },
    cacao: {
        terminos: ['cacao', 'chocolatada', 'nesquik', 'toddy'],
        incompatibles: ['yerba', 'cafe', 'te']
    },
    azucar: {
        terminos: ['azucar', 'azucar comun', 'azucar impalpable', 'azucar mascabo', 'azucar rubio'],
        incompatibles: ['edulcorante', 'sal', 'harina', 'arroz', 'fideos', 'leche']
    },
    edulcorante: {
        terminos: ['edulcorante', 'stevia', 'sucralosa', 'sacarina'],
        incompatibles: ['azucar', 'sal']
    },
    sal: {
        terminos: ['sal fina', 'sal gruesa', 'sal marina', 'sal parrillera'],
        incompatibles: ['azucar', 'harina']
    },
    galletitas: {
        terminos: ['galletitas', 'galletas', 'biscotti', 'crackers', 'dulces', 'rellenas', 'obleas', 'bizcochos', 'tostadas'],
        incompatibles: ['arroz', 'fideos', 'harina', 'leche', 'aceite', 'yerba', 'shampoo', 'jabon']
    },
    alfajor: {
        terminos: ['alfajor', 'alfajores', 'bocadito', 'conito'],
        incompatibles: ['leche', 'arroz', 'fideos', 'galletita', 'aceite', 'yerba', 'gaseosa', 'jugo', 'shampoo']
    },
    gaseosa: {
        terminos: ['gaseosa', 'cola', 'soda', 'bebida con gas', 'refresco'],
        incompatibles: ['jugo', 'agua', 'cerveza', 'vino', 'shampoo', 'jabon', 'detergente', 'arroz', 'fideos', 'aceite', 'leche', 'alfajor']
    },
    jugo: {
        terminos: ['jugo', 'jugos', 'multifruta', 'citrico', 'nectar', 'bicitrico', 'cepita', 'tang', 'clight'],
        incompatibles: ['leche', 'gaseosa', 'cerveza', 'arroz', 'fideos', 'aceite', 'shampoo', 'alfajor']
    },
    agua: {
        terminos: ['agua mineral', 'agua de mesa', 'agua sin gas', 'agua con gas', 'agua saborizada', 'saborizada'],
        incompatibles: ['gaseosa cola', 'cerveza', 'vino', 'aceite', 'leche', 'detergente', 'arroz', 'fideos']
    },
    cerveza: {
        terminos: ['cerveza', 'rubia', 'negra', 'ipa', 'apa', 'stout', 'lager', 'pilsen'],
        incompatibles: ['gaseosa', 'vino', 'jugo', 'agua', 'leche', 'aceite', 'arroz', 'fideos']
    },
    vino: {
        terminos: ['vino', 'malbec', 'cabernet', 'syrah', 'merlot', 'chardonnay', 'sauvignon', 'tinto', 'blanco', 'rosado'],
        incompatibles: ['cerveza', 'gaseosa', 'jugo', 'agua', 'aceite', 'arroz', 'fideos']
    },
    atun: {
        terminos: ['atun', 'lomitos de atun', 'desmenuzado', 'al agua', 'al aceite'],
        incompatibles: ['caballa', 'sardinas', 'arvejas', 'choclo', 'lentejas', 'fideos', 'arroz', 'leche']
    },
    conservas_vegetales: {
        terminos: ['arvejas', 'choclo', 'lentejas', 'porotos', 'garbanzos'],
        incompatibles: ['atun', 'fideos', 'arroz', 'leche']
    },
    detergente: {
        terminos: ['detergente', 'lavavajillas', 'detergente para platos'],
        incompatibles: ['jabon en pan', 'jabon de tocador', 'shampoo', 'lavandina', 'limpiador de pisos', 'suavizante', 'aceite', 'leche', 'arroz']
    },
    lavandina: {
        terminos: ['lavandina', 'cloro'],
        incompatibles: ['detergente', 'suavizante', 'shampoo', 'jabon']
    },
    suavizante: {
        terminos: ['suavizante', 'suavizante para ropa'],
        incompatibles: ['detergente', 'lavandina', 'jabon']
    },
    jabon_ropa: {
        terminos: ['jabon liquido para ropa', 'jabon en polvo', 'baja espuma', 'para lavarropas'],
        incompatibles: ['jabon de tocador', 'shampoo', 'detergente para platos']
    },
    jabon_tocador: {
        terminos: ['jabon de tocador', 'jabon en barra', 'jabon corporal'],
        incompatibles: ['jabon en polvo', 'detergente', 'shampoo', 'lavandina']
    },
    shampoo: {
        terminos: ['shampoo', 'champu', 'acondicionador', 'enjuague', 'crema de enjuague', 'balsamo capilar'],
        incompatibles: ['jabon de tocador', 'detergente', 'lavandina', 'leche', 'gaseosa', 'jugo', 'aceite', 'arroz']
    },
    desodorante: {
        terminos: ['desodorante', 'antitranspirante', 'bodyspray', 'roll on', 'aerosol'],
        incompatibles: ['shampoo', 'jabon', 'detergente']
    },
    dentifrico: {
        terminos: ['dentifrico', 'crema dental', 'pasta dental', 'anticaries'],
        incompatibles: ['shampoo', 'jabon', 'detergente']
    },
    papel_higienico: {
        terminos: ['papel higienico', 'hoja simple', 'doble hoja'],
        incompatibles: ['rollo de cocina', 'servilletas']
    },
    rollo_cocina: {
        terminos: ['rollo de cocina', 'toalla de papel', 'servilletas de papel'],
        incompatibles: ['papel higienico']
    },
    pan: {
        terminos: ['pan lactal', 'pan de molde', 'pan para panchos', 'pan para hamburguesas', 'pan rallado', 'rebozador'],
        incompatibles: ['galletitas', 'fideos', 'arroz', 'leche']
    }
};

// Generar compatibilidad de CATEGORIAS_PRODUCTO
const CATEGORIAS_PRODUCTO = {};
for (const key in DEFINICION_CATEGORIAS) {
    CATEGORIAS_PRODUCTO[key] = DEFINICION_CATEGORIAS[key].terminos;
}

// Stop words que no representan marcas ni productos
const STOP_WORDS = new Set([
    'de', 'del', 'en', 'para', 'con', 'sin', 'el', 'la', 'los', 'las', 'un', 'una',
    'unos', 'unas', 'tipo', 'x', 'al', 'por', 'y', 'o', 'gr', 'grs', 'g', 'kg',
    'kgs', 'kilo', 'kilos', 'l', 'lt', 'lts', 'litro', 'litros', 'ml', 'mls', 'cc',
    'u', 'unidades', 'comun', 'clasico', 'clasica', 'original'
]);

// Sabores y variantes descriptivas comunes
const SABORES_Y_VARIANTES = new Set([
    'pomelo', 'naranja', 'limon', 'cola', 'manzana', 'pera', 'uva', 'frutilla',
    'durazno', 'anana', 'multifruta', 'citrico', 'lima', 'vainilla', 'chocolate',
    'dulce', 'salado', 'amargo', 'suave', 'intenso', 'fuerte', 'extra', 'parboil',
    'largo', 'fino', 'entera', 'descremada', 'parcialmente', 'deslactosada',
    'zero', 'diet', 'light', 'cero', 'despalada', 'hierbas', 'compuesta', 'liviana', 'chocolatada'
]);

// Palabras que expresamente indican búsqueda genérica
const PALABRAS_GENERICAS = [
    'barato', 'barata', 'baratos', 'baratas',
    'economico', 'economica', 'economicos', 'economicas',
    'generico', 'generica', 'alternativa', 'comun', 'cualquiera'
];

// Accesorios y repuestos que deben rechazarse frente a productos principales de consumo
const ACCESORIOS_INCOMPATIBLES = [
    'vaso', 'vasos', 'termo', 'termos', 'mate de madera', 'bombilla', 'bombillas',
    'funda', 'fundas', 'repuesto', 'repuestos', 'tapa', 'tapas', 'dispenser', 'dosificador',
    'recipiente', 'cuchara', 'soporte', 'porta'
];

// Subcategorías generales y estandarizadas
const SUBCATEGORIAS_COMUNES = {
    'largo fino': 'largo fino',
    'doble carolina': 'doble carolina',
    'parboil': 'parboil',
    'carnaroli': 'carnaroli',
    'yamani': 'yamani',
    'tallarin': 'tallarines',
    'tallarines': 'tallarines',
    'spaghetti': 'tallarines',
    'tirabuzon': 'guiseros',
    'tirabuzones': 'guiseros',
    'mostachol': 'guiseros',
    'mostacholes': 'guiseros',
    'penne': 'guiseros',
    'descremada': 'descremada',
    'entera': 'entera',
    'deslactosada': 'deslactosada',
    'cremoso': 'cremoso',
    'mozzarella': 'mozzarella',
    'sardo': 'sardo',
    'reggianito': 'reggianito',
    'girasol': 'girasol',
    'oliva': 'oliva',
    'maiz': 'maiz',
    'con gas': 'con gas',
    'sin gas': 'sin gas',
    'rubia': 'rubia',
    'negra': 'negra',
    'ipa': 'ipa',
    'tinto': 'tinto',
    'blanco': 'blanco',
    'hoja simple': 'hoja simple',
    'doble hoja': 'doble hoja'
};

// Líneas y sub-marcas distintivas que definen identidad dentro de una categoría
const LINEAS_PRODUCTO = [
    'oro', 'clasica', 'clasico', 'original', 'premium', 'maximo', 'zero', 'light', 'diet', 'cero',
    'suave', 'intenso', 'especial', 'tradicional', 'con palo', 'despalada', 'seleccion', 'familiar'
];

// Extraer unidad y valor numérico de presentación (ej: "2.25L" -> { valor: 2.25, tipo: 'l', raw: '2.25l' }, "100 g. x 3 uni" -> { valor: 0.3, tipo: 'kg', raw: '100 g. x 3 uni' })
function extraerPresentacion(texto) {
    if (!texto || typeof texto !== 'string') return null;
    var raw = texto.toLowerCase();

    // 1. Multipack previo de peso: "3x 100gramos", "3 x 100g", "pack 3 x 100g", "pack x 3 de 100 g"
    var mMultiPesoPrev = raw.match(/(?:pack\s*(?:x\s*)?|x\s*)?(\d+)\s*(?:x|\*|de)\s*(\d+(?:[.,]\d+)?)\s*(kilos?|kilogramos?|kgs?|kg|k|gramos?|grs?|gr|g)\b/i);
    if (mMultiPesoPrev) {
        var countPrevP = parseInt(mMultiPesoPrev[1], 10);
        var uValPrevP = parseFloat(mMultiPesoPrev[2].replace(',', '.'));
        var isGPrevP = mMultiPesoPrev[3].toLowerCase().startsWith('g');
        var totalGPrevP = (isGPrevP ? uValPrevP : uValPrevP * 1000) * countPrevP;
        return { valor: totalGPrevP / 1000, tipo: 'kg', raw: mMultiPesoPrev[0].trim() };
    }

    // 2. Multipack posterior de peso: "100 g. x 3 uni", "100g x 3", "100 grs x 3", "100 g x 3 u"
    var mMultiPesoPost = raw.match(/(\d+(?:[.,]\d+)?)\s*(kilos?|kilogramos?|kgs?|kg|k|gramos?|grs?|gr|g)\b(?:\s*\.?)?\s*(?:x|\*)\s*(\d+)\s*(?:unidades?|unids?|unid|uni|un|u|paquetes?|paqs?|sobres?)?\b/i);
    if (mMultiPesoPost) {
        var uValPostP = parseFloat(mMultiPesoPost[1].replace(',', '.'));
        var isGPostP = mMultiPesoPost[2].toLowerCase().startsWith('g');
        var countPostP = parseInt(mMultiPesoPost[3], 10);
        var totalGPostP = (isGPostP ? uValPostP : uValPostP * 1000) * countPostP;
        return { valor: totalGPostP / 1000, tipo: 'kg', raw: mMultiPesoPost[0].trim() };
    }

    // 3. Multipack previo de volumen: "6 x 500 ml", "pack x 2 de 1.5 l"
    var mMultiVolPrev = raw.match(/(?:pack\s*(?:x\s*)?|x\s*)?(\d+)\s*(?:x|\*|de)\s*(\d+(?:[.,]\d+)?)\s*(litros?|lts?|lt|l|mililitros?|mls?|ml|cc)\b/i);
    if (mMultiVolPrev) {
        var countPrevV = parseInt(mMultiVolPrev[1], 10);
        var uValPrevV = parseFloat(mMultiVolPrev[2].replace(',', '.'));
        var isMlPrevV = mMultiVolPrev[3].toLowerCase().startsWith('m') || mMultiVolPrev[3].toLowerCase() === 'cc';
        var totalMlPrevV = (isMlPrevV ? uValPrevV : uValPrevV * 1000) * countPrevV;
        return { valor: totalMlPrevV / 1000, tipo: 'l', raw: mMultiVolPrev[0].trim() };
    }

    // 4. Multipack posterior de volumen: "500 ml x 6 uni", "1.5 l x 2"
    var mMultiVolPost = raw.match(/(\d+(?:[.,]\d+)?)\s*(litros?|lts?|lt|l|mililitros?|mls?|ml|cc)\b(?:\s*\.?)?\s*(?:x|\*)\s*(\d+)\s*(?:unidades?|unids?|unid|uni|un|u|botellas?|latas?|packs?)?\b/i);
    if (mMultiVolPost) {
        var uValPostV = parseFloat(mMultiVolPost[1].replace(',', '.'));
        var isMlPostV = mMultiVolPost[2].toLowerCase().startsWith('m') || mMultiVolPost[2].toLowerCase() === 'cc';
        var countPostV = parseInt(mMultiVolPost[3], 10);
        var totalMlPostV = (isMlPostV ? uValPostV : uValPostV * 1000) * countPostV;
        return { valor: totalMlPostV / 1000, tipo: 'l', raw: mMultiVolPost[0].trim() };
    }

    // Litros / Mililitros simple: 2.25l, 2,25 lts, 1.5 l, 500 ml, etc.
    var mVol = raw.match(/(\d+(?:[.,]\d+)?)\s*(litros?|lts?|lt|l|mililitros?|mls?|ml|cc)\b/);
    if (mVol) {
        var num = parseFloat(mVol[1].replace(',', '.'));
        var u = mVol[2].startsWith('m') || mVol[2] === 'cc' ? 'ml' : 'l';
        var valorLitros = u === 'ml' ? num / 1000 : num;
        return { valor: valorLitros, tipo: 'l', raw: mVol[0].trim() };
    }
    // Kilogramos / Gramos simple: 1kg, 1.5 kgs, 500g, 500 grs
    var mPeso = raw.match(/(\d+(?:[.,]\d+)?)\s*(kilos?|kilogramos?|kgs?|kg|k|gramos?|grs?|gr|g)\b/);
    if (mPeso) {
        var numP = parseFloat(mPeso[1].replace(',', '.'));
        var uP = mPeso[2].startsWith('g') ? 'g' : 'kg';
        var valorKg = uP === 'g' ? numP / 1000 : numP;
        return { valor: valorKg, tipo: 'kg', raw: mPeso[0].trim() };
    }
    // Unidades / Packs simple: pack x 3, x 4 un, 4 rollos, 4 u, 4 uni, 4 ud
    var mUn = raw.match(/(?:pack\s*x?\s*|x\s*)?(\d+)\s*(?:unidades?|unids?|unid|uni|uds?|ud|un|rollos?|sobres?|paquetes?|u)\b/);
    if (mUn) {
        var numU = parseInt(mUn[1], 10);
        return { valor: numU, tipo: 'un', raw: mUn[0].trim() };
    }
    return null;
}

// Extrae todas las subcadenas relevantes de un texto (palabras individuales, n-gramas de frases y sub-raíces)
function extraerSubcadenas(texto, minLen) {
    if (!minLen) minLen = 2;
    if (!texto || typeof texto !== 'string') return [];
    var norm = normalizar(texto);
    if (!norm) return [];

    var subcadenas = new Set();
    var tokens = norm.split(/\s+/).filter(function(t) { return t.length >= minLen; });

    // 1. Tokens individuales (palabras)
    for (var i = 0; i < tokens.length; i++) {
        var t = tokens[i];
        subcadenas.add(t);
        if (t.length >= 4) {
            for (var l = 3; l < t.length; l++) {
                subcadenas.add(t.substring(0, l));
            }
        }
    }

    // 2. N-gramas continuos de palabras (secuencias consecutivas)
    for (var nl = 2; nl <= tokens.length; nl++) {
        for (var ni = 0; ni <= tokens.length - nl; ni++) {
            var ngram = tokens.slice(ni, ni + nl).join(' ');
            if (ngram.length >= minLen) {
                subcadenas.add(ngram);
            }
        }
    }

    // 3. Cadena completa normalizada
    if (norm.length >= minLen) {
        subcadenas.add(norm);
    }

    return Array.from(subcadenas);
}

// Calcula las coincidencias de subcadenas entre dos textos cualesquiera (bidireccional)
function calcularCoincidenciasSubcadenas(textoA, textoB, minLen) {
    if (!minLen) minLen = 2;
    var normA = normalizar(textoA || '');
    var normB = normalizar(textoB || '');
    if (!normA || !normB) {
        return { coincidentes: [], cantidad: 0, tokensCoincidentes: 0, totalTokens: 0, porcentaje: 0, score: 0 };
    }

    var subsA = extraerSubcadenas(normA, minLen);
    var tokensA = normA.split(/\s+/).filter(function(t) { return t.length >= minLen; });
    var tokensB = normB.split(/\s+/).filter(function(t) { return t.length >= minLen; });

    var coincidentesSet = new Set();
    var score = 0;
    var tokensCoincidentes = 0;

    // Coincidencia exacta completa
    if (normA === normB) {
        coincidentesSet.add(normA);
        score += 100;
    } else if (normB.includes(normA)) {
        coincidentesSet.add(normA);
        score += 50;
    } else if (normA.includes(normB)) {
        coincidentesSet.add(normB);
        score += 40;
    }

    // Coincidencia de subcadenas de A en B
    for (var i = 0; i < subsA.length; i++) {
        var sub = subsA[i];
        if (normB.includes(sub)) {
            coincidentesSet.add(sub);
            score += (sub.includes(' ') ? 15 : 8) + Math.min(sub.length, 10);
        }
    }

    // Coincidencia de tokens
    for (var tIdx = 0; tIdx < tokensA.length; tIdx++) {
        var ta = tokensA[tIdx];
        var matched = false;
        for (var tbIdx = 0; tbIdx < tokensB.length; tbIdx++) {
            var tb = tokensB[tbIdx];
            if (ta === tb) {
                matched = true;
                coincidentesSet.add(ta);
                score += 12;
                break;
            } else if ((ta.length >= 2 && tb.includes(ta)) || (tb.length >= 2 && ta.includes(tb))) {
                matched = true;
                coincidentesSet.add(ta.length <= tb.length ? ta : tb);
                score += 6;
                break;
            }
        }
        if (matched) tokensCoincidentes++;
    }

    var porcentaje = tokensA.length > 0 ? (tokensCoincidentes / tokensA.length) : 0;
    return {
        coincidentes: Array.from(coincidentesSet),
        cantidad: coincidentesSet.size,
        tokensCoincidentes: tokensCoincidentes,
        totalTokens: tokensA.length,
        porcentaje: Math.round(porcentaje * 100) / 100,
        score: score
    };
}

// Búsqueda por subcadenas que obtiene la mayor cantidad de coincidencias posibles.
// Si no se provee 'candidatos', busca en todo el catálogo cerrado centralizado.
// Si se provee una lista de candidatos (strings u objetos), evalúa cada uno y retorna los coincidentes ordenados.
function buscarPorSubcadenas(query, candidatos, opciones) {
    if (!candidatos || !Array.isArray(candidatos) || candidatos.length === 0) {
        return catalogo.buscarPorSubcadenas(query, opciones || {});
    }

    var opts = opciones || {};
    var minLen = opts.minLongitudSubcadena || 2;
    var limite = opts.limite || 0;
    var resultados = [];

    for (var i = 0; i < candidatos.length; i++) {
        var cand = candidatos[i];
        var textoCand = '';
        if (typeof cand === 'string') {
            textoCand = cand;
        } else if (cand && typeof cand === 'object') {
            textoCand = cand.nombre || cand.nombre_completo || cand.producto || cand.titulo || cand.texto || '';
        }

        var match = calcularCoincidenciasSubcadenas(query, textoCand, minLen);
        if (match.cantidad > 0) {
            resultados.push({
                candidato: cand,
                texto: textoCand,
                score: match.score,
                cantidadCoincidencias: match.cantidad,
                subcadenasCoincidentes: match.coincidentes,
                tokensCoincidentes: match.tokensCoincidentes,
                porcentajeTokens: match.porcentaje
            });
        }
    }

    resultados.sort(function(a, b) {
        if (b.score !== a.score) return b.score - a.score;
        if (b.cantidadCoincidencias !== a.cantidadCoincidencias) return b.cantidadCoincidencias - a.cantidadCoincidencias;
        return b.porcentajeTokens - a.porcentajeTokens;
    });

    if (limite > 0 && resultados.length > limite) {
        return resultados.slice(0, limite);
    }

    return resultados;
}

// Extrae todos los atributos estructurados de un producto de cualquier categoría
function extraerAtributos(texto) {
    if (!texto || typeof texto !== 'string') {
        return { categoria: null, subcategoria: null, marca: null, linea: null, variedad: null, presentacion: null, esAccesorio: false, textoNorm: '' };
    }
    var tNorm = normalizar(texto);
    var pres = extraerPresentacion(texto);

    // 1. Categoría
    var cat = null;
    var cKeys = Object.keys(DEFINICION_CATEGORIAS);
    for (var j = 0; j < cKeys.length; j++) {
        var k = cKeys[j];
        if (DEFINICION_CATEGORIAS[k].terminos.some(function(t) {
            if (t.length <= 4) {
                var rx = new RegExp('(?:^|\\s)' + t.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') + '(?:$|\\s)', 'i');
                return rx.test(tNorm);
            }
            return tNorm.includes(t);
        })) {
            cat = k;
            break;
        }
    }

    // 2. Subcategoría
    var subcat = null;
    var skKeys = Object.keys(SUBCATEGORIAS_COMUNES);
    for (var s = 0; s < skKeys.length; s++) {
        var sk = skKeys[s];
        if (tNorm.includes(sk)) {
            subcat = SUBCATEGORIAS_COMUNES[sk];
            break;
        }
    }

    // 3. Marca
    var marca = null;
    var marcasOrdenadas = MARCAS_CONOCIDAS.slice().sort(function(a, b) { return b.length - a.length; });
    for (var i = 0; i < marcasOrdenadas.length; i++) {
        var m = marcasOrdenadas[i];
        var regex = new RegExp('(?:^|\\s)' + m.replace('-', '[-\\s]') + '(?:$|\\s)', 'i');
        if (regex.test(tNorm)) {
            marca = m;
            break;
        }
    }

    // 4. Línea
    var linea = null;
    for (var l = 0; l < LINEAS_PRODUCTO.length; l++) {
        var lp = LINEAS_PRODUCTO[l];
        var rxL = new RegExp('(?:^|\\s)' + lp + '(?:$|\\s)', 'i');
        if (rxL.test(tNorm)) {
            linea = lp;
            break;
        }
    }

    // 5. Variedad (sabor o variante descriptiva)
    var variedad = null;
    var varArray = Array.from(SABORES_Y_VARIANTES);
    for (var v = 0; v < varArray.length; v++) {
        var vr = varArray[v];
        var rxV = new RegExp('(?:^|\\s)' + vr + '(?:$|\\s)', 'i');
        if (rxV.test(tNorm)) {
            variedad = vr;
            break;
        }
    }

    // 6. Accesorio
    var esAccesorio = false;
    for (var a = 0; a < ACCESORIOS_INCOMPATIBLES.length; a++) {
        var acc = ACCESORIOS_INCOMPATIBLES[a];
        var rxAcc = new RegExp('(?:^|\\s)' + acc + '(?:$|\\s)', 'i');
        if (rxAcc.test(tNorm)) {
            esAccesorio = true;
            break;
        }
    }

    return {
        categoria: cat,
        subcategoria: subcat,
        marca: marca,
        linea: linea,
        variedad: variedad,
        presentacion: pres,
        esAccesorio: esAccesorio,
        textoNorm: tNorm
    };
}

// Normaliza el precio por unidad base (por kg, litro o unidad) para comparabilidad objetiva
function calcularPrecioNormalizado(item) {
    if (!item) return null;
    var precio = typeof item.precio === 'number' ? item.precio : parsePrecio(item.precioStr);
    if (!precio || precio <= 0) return null;
    var pres = extraerPresentacion(item.nombre || item.producto || '');
    if (!pres || !pres.valor || pres.valor <= 0) {
        return {
            precioBase: precio,
            precioNormalizado: precio,
            unidadBase: 'unidad',
            descripcion: formatoMoneda(precio) + ' c/u'
        };
    }
    var precioNorm = Math.round((precio / pres.valor) * 100) / 100;
    var unidadStr = pres.tipo === 'kg' ? 'kg' : (pres.tipo === 'l' ? 'litro' : 'unidad');
    return {
        precioBase: precio,
        precioNormalizado: precioNorm,
        unidadBase: unidadStr,
        descripcion: formatoMoneda(precioNorm) + ' por ' + unidadStr
    };
}

// Motor General de Comparabilidad: Determina si dos productos son comercialmente comparables
function sonComparables(itemA, itemB, queryOriginal) {
    var qNorm = normalizar(queryOriginal || '');
    var intencion = detectarIntencion(queryOriginal || '');
    var nomA = (itemA && typeof itemA === 'object') ? (itemA.nombre || itemA.producto || '') : String(itemA || '');
    var nomB = (itemB && typeof itemB === 'object') ? (itemB.nombre || itemB.producto || '') : String(itemB || '');
    var attrA = extraerAtributos(nomA);
    var attrB = extraerAtributos(nomB);

    // 1. Accesorios vs principales
    var queryPideAccesorio = ACCESORIOS_INCOMPATIBLES.some(function(acc) { return qNorm.includes(acc); });
    if (!queryPideAccesorio && (attrA.esAccesorio || attrB.esAccesorio)) {
        return { comparable: false, motivo: 'Uno de los productos es un accesorio/repuesto y no un producto principal de consumo.' };
    }

    // 2. Categoría
    if (attrA.categoria && attrB.categoria && attrA.categoria !== attrB.categoria) {
        return { comparable: false, motivo: 'Categorías incompatibles (' + attrA.categoria + ' vs ' + attrB.categoria + ').' };
    }

    // 3. Marca: Si la intención incluye marca, ambos deben poseer dicha marca
    if (intencion.marca) {
        var marcaReq = normalizar(intencion.marca);
        var matchA = attrA.textoNorm.includes(marcaReq);
        var matchB = attrB.textoNorm.includes(marcaReq);
        if (!matchA || !matchB) {
            return { comparable: false, motivo: 'La búsqueda requería marca específica "' + intencion.marca.toUpperCase() + '".' };
        }
    }

    // 4. Línea o sub-marca
    if (intencion.queryNormalizada) {
        for (var i = 0; i < LINEAS_PRODUCTO.length; i++) {
            var lp = LINEAS_PRODUCTO[i];
            if (intencion.queryNormalizada.includes(lp)) {
                var aTiene = attrA.textoNorm.includes(lp);
                var bTiene = attrB.textoNorm.includes(lp);
                if (aTiene !== bTiene) {
                    return { comparable: false, motivo: 'Difieren en la línea específica requerida ("' + lp.toUpperCase() + '").' };
                }
            }
        }
    }

    // 5. Variedad o sabor
    if (intencion.queryNormalizada) {
        var variedades = Array.from(SABORES_Y_VARIANTES);
        for (var j = 0; j < variedades.length; j++) {
            var v = variedades[j];
            if (intencion.queryNormalizada.includes(v)) {
                var aVar = attrA.textoNorm.includes(v);
                var bVar = attrB.textoNorm.includes(v);
                if (!aVar || !bVar) {
                    return { comparable: false, motivo: 'Se solicitó sabor/variedad "' + v.toUpperCase() + '" y no coincide en ambos productos.' };
                }
            }
        }
    }

    // 6. Presentación / escala
    if (attrA.presentacion && attrB.presentacion && attrA.presentacion.tipo === attrB.presentacion.tipo) {
        var ratio = attrA.presentacion.valor / attrB.presentacion.valor;
        if (ratio > 2.5 || ratio < 0.4) {
            return { comparable: false, motivo: 'Presentaciones fuera de escala comparable (' + attrA.presentacion.raw + ' vs ' + attrB.presentacion.raw + ').' };
        }
    }

    // 6.5. Longitud de rollo de papel higiénico (30m estándar vs 100m Max)
    var esPapelA = attrA.categoria === 'papel_higienico' || attrA.textoNorm.includes('papel higienico') || attrA.textoNorm.includes('higienol');
    var esPapelB = attrB.categoria === 'papel_higienico' || attrB.textoNorm.includes('papel higienico') || attrB.textoNorm.includes('higienol');
    if (esPapelA || esPapelB) {
        var aEs100m = attrA.textoNorm.includes('100') || attrA.textoNorm.includes('max') || attrA.textoNorm.includes('mega');
        var bEs100m = attrB.textoNorm.includes('100') || attrB.textoNorm.includes('max') || attrB.textoNorm.includes('mega');
        if (aEs100m !== bEs100m) {
            return { comparable: false, motivo: 'Discrepancia en longitud de rollo de papel higiénico (100 mts vs 30 mts).' };
        }
    }

    return { comparable: true, motivo: 'Productos equivalentes y comparables.' };
}

// Detecta la intención de búsqueda: ESPECÍFICA o GENÉRICA de forma general para todas las categorías
function detectarIntencion(queryOriginal) {
    var rawText = '';
    if (typeof queryOriginal === 'string') {
        rawText = queryOriginal;
    } else if (queryOriginal && typeof queryOriginal === 'object') {
        rawText = [queryOriginal.nombre_completo, queryOriginal.producto, queryOriginal.marca, queryOriginal.variante, queryOriginal.nombre].filter(Boolean).join(' ');
    }

    var queryNorm = normalizar(rawText);
    if (!queryNorm) {
        return { tipo: 'GENERICA', marca: null, presentacion: null, categoria: null, palabras: [], queryNormalizada: '' };
    }

    var tienePalabraGenerica = PALABRAS_GENERICAS.some(function(pg) {
        return queryNorm.includes(pg);
    });

    var pres = extraerPresentacion(rawText);

    // 1. Identificar categoría
    var catEncontrada = null;
    var defKeys = Object.keys(DEFINICION_CATEGORIAS);
    for (var j = 0; j < defKeys.length; j++) {
        var cKey = defKeys[j];
        var def = DEFINICION_CATEGORIAS[cKey];
        if (def.terminos.some(function(t) { return queryNorm.includes(t); })) {
            catEncontrada = cKey;
            break;
        }
    }

    // 2. Detectar si contiene alguna marca conocida
    var marcaEncontrada = null;
    var marcasOrdenadas = MARCAS_CONOCIDAS.slice().sort(function(a, b) { return b.length - a.length; });
    for (var i = 0; i < marcasOrdenadas.length; i++) {
        var m = marcasOrdenadas[i];
        var regex = new RegExp('(?:^|\\s)' + m.replace('-', '[-\\s]') + '(?:$|\\s)', 'i');
        if (regex.test(queryNorm)) {
            marcaEncontrada = m;
            break;
        }
    }

    var palabras = queryNorm.split(/\s+/);
    var esEspecifica = false;

    // 3. Si no hay marca conocida pero hay palabras que califican (no stop words, no unidades, no categoría, no sabores)
    if (!marcaEncontrada && !tienePalabraGenerica) {
        var palabrasCalificadoras = palabras.filter(function(p) {
            if (STOP_WORDS.has(p)) return false;
            if (SABORES_Y_VARIANTES.has(p)) return false;
            if (PALABRAS_GENERICAS.includes(p)) return false;
            if (pres && pres.raw.toLowerCase().includes(p)) return false;
            if (/^\d+([.,]\d+)?$/.test(p)) return false;
            if (catEncontrada && DEFINICION_CATEGORIAS[catEncontrada]) {
                if (DEFINICION_CATEGORIAS[catEncontrada].terminos.some(function(t) { return t === p || t.includes(p); })) {
                    return false;
                }
            }
            return p.length >= 2;
        });

        if (palabrasCalificadoras.length > 0) {
            marcaEncontrada = palabrasCalificadoras.join(' ');
            esEspecifica = true;
        }
    } else if (marcaEncontrada && !tienePalabraGenerica) {
        esEspecifica = true;
    }

    return {
        tipo: esEspecifica ? 'ESPECIFICA' : 'GENERICA',
        marca: marcaEncontrada,
        presentacion: pres,
        categoria: catEncontrada,
        palabras: palabras,
        queryNormalizada: queryNorm
    };
}

// Obtiene la configuración completa de búsqueda para pasarla al browser screencast
function obtenerConfiguracionBusqueda(queryOriginal) {
    var intencion = detectarIntencion(queryOriginal);
    var defCat = intencion.categoria && DEFINICION_CATEGORIAS[intencion.categoria] ? DEFINICION_CATEGORIAS[intencion.categoria] : null;
    
    var terminosValidos = defCat ? defCat.terminos : [];
    var terminosIncompatibles = defCat ? defCat.incompatibles : [];
    
    var palabrasRequeridas = [];
    if (intencion.marca) {
        palabrasRequeridas = normalizar(intencion.marca).split(/\s+/).filter(function(w) {
            return w.length >= 2 && !STOP_WORDS.has(w);
        });
    }

    var variantesRequeridas = [];
    var qNorm = intencion.queryNormalizada || '';
    if (qNorm) {
        SABORES_Y_VARIANTES.forEach(function(v) {
            if (qNorm.includes(v)) {
                variantesRequeridas.push(v);
            }
        });
    }

    return {
        queryOriginal: queryOriginal,
        queryNormalizada: qNorm,
        tipo: intencion.tipo,
        categoria: intencion.categoria,
        terminosValidos: terminosValidos,
        terminosIncompatibles: terminosIncompatibles,
        marca: intencion.marca,
        palabrasRequeridas: palabrasRequeridas,
        variantesRequeridas: variantesRequeridas,
        presentacion: intencion.presentacion
    };
}

function validarCoincidencia(queryOriginal, resultado) {
    var intencion = detectarIntencion(queryOriginal);
    var nombreEncontrado = (resultado && (resultado.nombre || resultado.nombre_encontrado)) || '';
    var matchSub = calcularCoincidenciasSubcadenas(queryOriginal, nombreEncontrado);

    var res = _validarCoincidenciaBase(queryOriginal, resultado, intencion, nombreEncontrado);
    if (res) {
        res.subcadenasCoincidentes = matchSub.coincidentes;
        res.cantidadCoincidencias = matchSub.cantidad;
        res.porcentajeCoincidencia = matchSub.porcentaje;
        res.scoreSubcadenas = matchSub.score;
    }
    return res;
}

function _validarCoincidenciaBase(queryOriginal, resultado, intencion, nombreEncontrado) {
    var nombreNorm = normalizar(nombreEncontrado);
    var precioStr = (resultado && resultado.precioStr) || '';
    var stockRaw = normalizar((resultado && resultado.stockRaw) || '');

    // 1. Detección de "No encontrado"
    if (!nombreEncontrado ||
        nombreNorm.includes('no encontrado') ||
        nombreNorm.includes('sin resultados') ||
        nombreNorm === 'n/d' ||
        resultado.precio === null && !nombreNorm) {
        return {
            estado: 'NO ENCONTRADO',
            valido: false,
            motivo: 'El producto no fue encontrado en el catálogo del supermercado.',
            intencion: intencion.tipo,
            marca: intencion.marca
        };
    }

    // 2. Detección de "Sin stock"
    if (stockRaw.includes('sin stock') ||
        stockRaw.includes('agotado') ||
        nombreNorm.includes('sin stock') ||
        nombreNorm.includes('agotado') ||
        precioStr.toLowerCase().includes('sin stock') ||
        precioStr.toLowerCase().includes('agotado')) {
        return {
            estado: 'SIN STOCK',
            valido: false,
            motivo: 'El producto existe en el catálogo pero se encuentra agotado / sin stock.',
            intencion: intencion.tipo,
            marca: intencion.marca
        };
    }

    // 2.5. Rechazo de productos accesorios si la consulta buscaba un producto de consumo principal
    var queryPideAccesorio = ACCESORIOS_INCOMPATIBLES.some(function(acc) { return intencion.queryNormalizada.includes(acc); });
    if (!queryPideAccesorio) {
        for (var a = 0; a < ACCESORIOS_INCOMPATIBLES.length; a++) {
            var accItem = ACCESORIOS_INCOMPATIBLES[a];
            var rxAcc = new RegExp('(?:^|\\s)' + accItem + '(?:$|\\s)', 'i');
            if (rxAcc.test(nombreNorm)) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'El producto devuelto (' + nombreEncontrado + ') es un accesorio/repuesto ("' + accItem.toUpperCase() + '") y no un producto principal.',
                    intencion: intencion.tipo,
                    marca: intencion.marca
                };
            }
        }
    }

    // 2.7. VALIDACIÓN DIRECTA MEDIANTE DICCIONARIO DE NOMBRES DE SUPERMERCADOS
    if (catalogo.buscarPorDiccionarioSupermercado) {
        var matchDict = catalogo.buscarPorDiccionarioSupermercado(nombreEncontrado);
        if (matchDict && matchDict.item) {
            var itemDict = matchDict.item;
            var targetQueryCat = catalogo.buscarEnCatalogo(queryOriginal);
            if (!targetQueryCat && (resultado.cantidad || resultado.unidad)) {
                targetQueryCat = catalogo.buscarEnCatalogo({
                    producto: queryOriginal,
                    cantidad: resultado.cantidad,
                    unidad: resultado.unidad
                });
            }

            var esCoherente = false;
            if (targetQueryCat) {
                if (targetQueryCat.id === itemDict.id) {
                    esCoherente = true;
                } else if (targetQueryCat.categoria === itemDict.categoria) {
                    if (intencion.tipo === 'GENERICA') {
                        esCoherente = true;
                    } else if (normalizar(targetQueryCat.marca) === normalizar(itemDict.marca) || ((normalizar(targetQueryCat.marca) === 'lucchetti' || normalizar(targetQueryCat.marca) === 'luchetti') && (normalizar(itemDict.marca) === 'lucchetti' || normalizar(itemDict.marca) === 'luchetti'))) {
                        if (targetQueryCat.variante && itemDict.variante) {
                            var vT = normalizar(targetQueryCat.variante);
                            var vI = normalizar(itemDict.variante);
                            if (vT === vI) {
                                esCoherente = true;
                            } else if (targetQueryCat.categoria === 'yerba' && ((vT.includes('suave') && vI.includes('tradicional')) || (vT.includes('tradicional') && vI.includes('suave')))) {
                                esCoherente = true;
                            } else if (targetQueryCat.categoria === 'leche' && ((vT.includes('entera') && vI.includes('clasica')) || (vT.includes('clasica') && vI.includes('entera')))) {
                                esCoherente = true;
                            } else if ((vT.includes('lima') && vI.includes('lima')) || (vT.includes('limon') && vI.includes('limon'))) {
                                esCoherente = true;
                            } else if ((vT.includes('tallarin') || vT.includes('tallarines')) && (vI.includes('tallarin') || vI.includes('tallarines'))) {
                                esCoherente = true;
                            } else if ((targetQueryCat.id && targetQueryCat.id.includes('max')) !== (itemDict.id && itemDict.id.includes('max'))) {
                                esCoherente = false;
                            } else {
                                esCoherente = false;
                            }
                        } else {
                            esCoherente = true;
                        }
                    }
                }
            } else {
                var marcaDictNorm = normalizar(itemDict.marca);
                var catDict = itemDict.categoria;
                var coincideCat = !intencion.categoria || intencion.categoria === catDict;
                var coincideMarca = !intencion.marca || normalizar(intencion.marca) === marcaDictNorm;
                if (coincideCat && coincideMarca) {
                    esCoherente = true;
                }
            }

            if (esCoherente) {
                var presEnc = extraerPresentacion(nombreEncontrado);
                var presEquiv = true;
                if (presEnc) {
                    var uEnc = presEnc.tipo === 'l' ? 'L' : (presEnc.tipo === 'kg' ? 'kg' : 'un');
                    presEquiv = catalogo.esPresentacionEquivalente(presEnc.valor, uEnc, itemDict.cantidad, itemDict.unidad);
                }

                if (presEquiv) {
                    return {
                        estado: 'VALIDADA',
                        valido: true,
                        motivo: 'Coincidencia validada mediante diccionario oficial de supermercados (' + itemDict.nombre_completo + ').',
                        intencion: 'ESPECIFICA',
                        marca: itemDict.marca,
                        itemCatalogo: itemDict,
                        diccionarioMatch: matchDict,
                        precioNormalizado: calcularPrecioNormalizado({ nombre: nombreEncontrado, precio: resultado.precio, precioStr: resultado.precioStr })
                    };
                }
            }
        }
    }

    // 2.8. VALIDACIÓN ESTRICTA CONTRA CATÁLOGO CERRADO
    var itemCat = catalogo.buscarEnCatalogo(queryOriginal);
    if (!itemCat && (resultado.cantidad || resultado.unidad)) {
        itemCat = catalogo.buscarEnCatalogo({
            producto: queryOriginal,
            cantidad: resultado.cantidad,
            unidad: resultado.unidad
        });
    }

    if (itemCat) {
        // A) Validación estricta de MARCA requerida
        var marcaCatNorm = normalizar(itemCat.marca);
        var marcaCatSinGuion = marcaCatNorm.replace(/-/g, ' ').trim();
        var palabrasMarcaCat = marcaCatNorm.split(/\s+/).filter(function(w) { return !STOP_WORDS.has(w); });
        var tieneMarcaCat = palabrasMarcaCat.every(function(m) {
            if (m === 'lucchetti' || m === 'luchetti') {
                return nombreNorm.includes('lucchetti') || nombreNorm.includes('luchetti');
            }
            var rxM = new RegExp('(?:^|\\s)' + m.replace('-', '[-\\s]') + '(?:$|\\s)', 'i');
            return rxM.test(nombreNorm);
        });

        if (!tieneMarcaCat) {
            return {
                estado: 'COINCIDENCIA NO VÁLIDA',
                valido: false,
                motivo: 'Marca requerida "' + itemCat.marca.toUpperCase() + '" no coincide con el producto devuelto ("' + nombreEncontrado + '").',
                intencion: 'ESPECIFICA',
                marca: itemCat.marca
            };
        }

        // Rechazar si contiene otra marca conocida de la categoría (evitando falsos positivos por variantes con guion)
        for (var mIdx = 0; mIdx < MARCAS_CONOCIDAS.length; mIdx++) {
            var mOtra = MARCAS_CONOCIDAS[mIdx];
            var mOtraSinGuion = mOtra.replace(/-/g, ' ').trim();
            var esMismaMarca = (mOtraSinGuion === marcaCatSinGuion) ||
                marcaCatSinGuion.includes(mOtraSinGuion) ||
                mOtraSinGuion.includes(marcaCatSinGuion) ||
                ((marcaCatSinGuion === 'lucchetti' || marcaCatSinGuion === 'luchetti') && (mOtraSinGuion === 'lucchetti' || mOtraSinGuion === 'luchetti'));
            if (!esMismaMarca) {
                var rxOtra = new RegExp('(?:^|\\s)' + mOtra.replace('-', '[-\\s]') + '(?:$|\\s)', 'i');
                if (rxOtra.test(nombreNorm)) {
                    return {
                        estado: 'COINCIDENCIA NO VÁLIDA',
                        valido: false,
                        motivo: 'Se detectó marca competidora "' + mOtra.toUpperCase() + '" cuando se requería "' + itemCat.marca.toUpperCase() + '".',
                        intencion: 'ESPECIFICA',
                        marca: itemCat.marca
                    };
                }
            }
        }

        // A.2) Validación estricta de CATEGORÍA E INCOMPATIBILIDADES
        if (itemCat.categoria && DEFINICION_CATEGORIAS[itemCat.categoria]) {
            var defCatCat = DEFINICION_CATEGORIAS[itemCat.categoria];
            if (defCatCat.incompatibles) {
                for (var incIdx = 0; incIdx < defCatCat.incompatibles.length; incIdx++) {
                    var incTerm = defCatCat.incompatibles[incIdx];
                    var rxInc = new RegExp('(?:^|\\s)' + incTerm.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') + '(?:$|\\s)', 'i');
                    if (rxInc.test(nombreNorm) || (incTerm.includes(' ') && nombreNorm.includes(incTerm))) {
                        return {
                            estado: 'COINCIDENCIA NO VÁLIDA',
                            valido: false,
                            motivo: 'El producto devuelto (' + nombreEncontrado + ') contiene "' + incTerm.toUpperCase() + '", incompatible con la categoría requerida (' + itemCat.categoria.toUpperCase() + ').',
                            intencion: 'ESPECIFICA',
                            marca: itemCat.marca
                        };
                    }
                }
            }

            // Exigencia de término de categoría para leche (no puede ser solo marca y tamaño)
            if (itemCat.categoria === 'leche') {
                var tieneTerminoLeche = ['leche', 'lactea', 'uht'].some(function(t) {
                    var rxT = new RegExp('(?:^|\\s)' + t + '(?:$|\\s)', 'i');
                    return rxT.test(nombreNorm);
                });
                var esAliasDicc = itemCat._normNombresSupermercados && itemCat._normNombresSupermercados.some(function(alias) {
                    return alias === nombreNorm || nombreNorm.includes(alias) || alias.includes(nombreNorm);
                });
                if (!tieneTerminoLeche && !esAliasDicc) {
                    return {
                        estado: 'COINCIDENCIA NO VÁLIDA',
                        valido: false,
                        motivo: 'El producto devuelto (' + nombreEncontrado + ') no contiene ningún término lácteo válido ("LECHE").',
                        intencion: 'ESPECIFICA',
                        marca: itemCat.marca
                    };
                }
            }
        }

        // B) Validación estricta de VARIANTE / SABOR requerida
        if (itemCat.variante) {
            var varCatNorm = normalizar(itemCat.variante);
            var esBase = ['original', 'tradicional', 'clasica', 'clasico', 'comun', 'entera', 'lima limon', 'suave'].some(function(b) {
                return varCatNorm.includes(b);
            });

            // Rechazo preventivo de variantes incompatibles conocidas para productos base (ej: leche)
            if (itemCat.categoria === 'leche' && esBase) {
                var variantesIncompatiblesLeche = ['protein', 'proteina', 'proteinas', 'extra protein', 'descremada', 'deslactosada', 'chocolatada', 'liviana', 'sin lactosa', 'calcio', 'fibra', 'cardio', 'hierro', 'bio'];
                for (var vIdx = 0; vIdx < variantesIncompatiblesLeche.length; vIdx++) {
                    var vInc = variantesIncompatiblesLeche[vIdx];
                    if (!intencion.queryNormalizada.includes(vInc)) {
                        var rxVInc = new RegExp('(?:^|\\s)' + vInc + '(?:$|\\s)', 'i');
                        if (rxVInc.test(nombreNorm)) {
                            return {
                                estado: 'COINCIDENCIA NO VÁLIDA',
                                valido: false,
                                motivo: 'Se detectó variante ajena "' + vInc.toUpperCase() + '" cuando se requería "' + itemCat.variante.toUpperCase() + '".',
                                intencion: 'ESPECIFICA',
                                marca: itemCat.marca
                            };
                        }
                    }
                }
            }

            var palabrasVar = varCatNorm.split(/\s+/).filter(function(w) { return !STOP_WORDS.has(w); });
            var queryMencionaVariante = palabrasVar.some(function(v) { return intencion.queryNormalizada.includes(v); });
            var presQuery = extraerPresentacion(queryOriginal);
            var esBusquedaEstricta = queryMencionaVariante || (presQuery !== null);

            if (esBusquedaEstricta) {
                if (queryMencionaVariante || !esBase) {
                    var tieneVariante = palabrasVar.every(function(v) { return nombreNorm.includes(v); });
                    if (!tieneVariante && varCatNorm.includes('lima') && varCatNorm.includes('limon')) {
                        tieneVariante = nombreNorm.includes('lima') || nombreNorm.includes('limon') || nombreNorm.includes('sprite') || nombreNorm.includes('7up');
                    }
                    if (!tieneVariante && (varCatNorm.includes('tallarin') || varCatNorm.includes('tallarines'))) {
                        tieneVariante = nombreNorm.includes('tallarin') || nombreNorm.includes('tallarines');
                    }
                    if (!tieneVariante && (itemCat.categoria === 'yerba' || (itemCat._normProducto && itemCat._normProducto.includes('yerba')))) {
                        if (nombreNorm.includes('suave') || nombreNorm.includes('tradicional') || nombreNorm.includes('con palo') || nombreNorm.includes('clasica')) {
                            tieneVariante = true;
                        }
                    }
                    if (!tieneVariante && (itemCat.categoria === 'leche' || (itemCat._normProducto && itemCat._normProducto.includes('leche')))) {
                        // Para leche, 'entera', 'clasica' y '3%' representan la leche entera estándar
                        if ((varCatNorm.includes('entera') || varCatNorm.includes('clasica')) && (nombreNorm.includes('clasica') || nombreNorm.includes('entera') || nombreNorm.includes('3%'))) {
                            tieneVariante = true;
                        }
                    }
                    if (!tieneVariante && (itemCat.categoria === 'galletitas' || (itemCat._normProducto && itemCat._normProducto.includes('galletita')))) {
                        // Para galletitas Criollitas/de agua, 'clasicas', 'original', 'crackers' y 'de agua' son equivalentes
                        if ((varCatNorm.includes('clasica') || varCatNorm.includes('clasicas') || varCatNorm.includes('original')) &&
                            (nombreNorm.includes('clasica') || nombreNorm.includes('clasicas') || nombreNorm.includes('original') || nombreNorm.includes('crackers') || nombreNorm.includes('de agua') || nombreNorm.includes('saladas'))) {
                            tieneVariante = true;
                        }
                    }
                    if (!tieneVariante) {
                        return {
                            estado: 'COINCIDENCIA NO VÁLIDA',
                            valido: false,
                            motivo: 'Variante/sabor "' + itemCat.variante + '" no presente en el resultado encontrado ("' + nombreEncontrado + '").',
                            intencion: 'ESPECIFICA',
                            marca: itemCat.marca
                        };
                    }
                }

                // Rechazar si contiene otra variante/sabor excluyente que contradiga la variante esperada
                var saboresArr = Array.from(SABORES_Y_VARIANTES);
                for (var sIdx = 0; sIdx < saboresArr.length; sIdx++) {
                    var sabOtra = saboresArr[sIdx];
                    if (!varCatNorm.includes(sabOtra)) {
                        // Si el término es parte de la marca o nombre base del producto (ej: 'cola' en 'coca cola'), no es excluyente
                        if (itemCat._normMarca.includes(sabOtra) || itemCat._normProducto.includes(sabOtra)) {
                            continue;
                        }
                        // Excepciones conocidas: 'limon' o 'lima' para Sprite o 7UP no es incompatible
                        if ((itemCat._normMarca.includes('sprite') || itemCat._normMarca.includes('7up')) && (sabOtra === 'limon' || sabOtra === 'lima')) {
                            continue;
                        }
                        // Excepción para yerba mate: 'suave' y 'tradicional' son variantes base compatibles entre sí
                        if ((itemCat.categoria === 'yerba' || (itemCat._normProducto && itemCat._normProducto.includes('yerba'))) && (sabOtra === 'suave' || sabOtra === 'tradicional')) {
                            continue;
                        }
                        // Excepción para leche: 'clasica', 'entera' y '3%' son variantes base compatibles entre sí
                        if ((itemCat.categoria === 'leche' || (itemCat._normProducto && itemCat._normProducto.includes('leche'))) && (sabOtra === 'entera' || sabOtra === 'clasica' || sabOtra === '3%')) {
                            continue;
                        }
                        // Excepción para galletitas: 'clasica', 'clasicas', 'original' y 'salado' son variantes base compatibles entre sí
                        if ((itemCat.categoria === 'galletitas' || (itemCat._normProducto && itemCat._normProducto.includes('galletita'))) && (sabOtra === 'original' || sabOtra === 'clasica' || sabOtra === 'clasicas' || sabOtra === 'salado')) {
                            continue;
                        }
                        var rxSabOtra = new RegExp('(?:^|\\s)' + sabOtra + '(?:$|\\s)', 'i');
                        if (rxSabOtra.test(nombreNorm)) {
                            return {
                                estado: 'COINCIDENCIA NO VÁLIDA',
                                valido: false,
                                motivo: 'Se detectó variante ajena "' + sabOtra.toUpperCase() + '" cuando se requería "' + itemCat.variante.toUpperCase() + '".',
                                intencion: 'ESPECIFICA',
                                marca: itemCat.marca
                            };
                        }
                    }
                }
            }
        }

        // C) Validación estricta de PRESENTACIÓN (cantidad y unidad)
        var presEncontradaCat = extraerPresentacion(nombreEncontrado);
        if (presEncontradaCat) {
            var unidEnc = presEncontradaCat.tipo === 'l' ? 'L' : (presEncontradaCat.tipo === 'kg' ? 'kg' : 'un');
            if (!catalogo.esPresentacionEquivalente(presEncontradaCat.valor, unidEnc, itemCat.cantidad, itemCat.unidad)) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'Presentación incompatible: solicitada ' + itemCat.cantidad + ' ' + itemCat.unidad + ' vs encontrada ' + presEncontradaCat.raw + '.',
                    intencion: 'ESPECIFICA',
                    marca: itemCat.marca
                };
            }
        }

        // D) Validación estricta de LONGITUD DE ROLLO para PAPEL HIGIÉNICO (30 mts vs 100 mts / Max)
        if (itemCat.categoria === 'limpieza' || itemCat.categoria === 'papel_higienico' || (itemCat._normProducto && (itemCat._normProducto.includes('papel higienico') || itemCat._normProducto.includes('higienol')))) {
            var esPeticionMax = (itemCat.id && itemCat.id.includes('max')) || (itemCat.nombre_completo && itemCat.nombre_completo.toLowerCase().includes('max')) || intencion.queryNormalizada.includes('max') || intencion.queryNormalizada.includes('100');
            var esResultadoMax = nombreNorm.includes('max') || nombreNorm.includes('100 mts') || nombreNorm.includes('100 m') || nombreNorm.includes('100m') || nombreNorm.includes('mega');

            if (!esPeticionMax && esResultadoMax) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'Línea de papel higiénico incompatible: se encontró "Max / 100 mts" cuando se requería presentación estándar (30 mts).',
                    intencion: 'ESPECIFICA',
                    marca: itemCat.marca
                };
            }
            if (esPeticionMax && !esResultadoMax) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'Línea de papel higiénico incompatible: se requiere presentación "Max / 100 mts".',
                    intencion: 'ESPECIFICA',
                    marca: itemCat.marca
                };
            }
        }

        return {
            estado: 'VALIDADA',
            valido: true,
            motivo: 'Coincidencia estricta con catálogo validada (' + itemCat.nombre_completo + ').',
            intencion: 'ESPECIFICA',
            marca: itemCat.marca,
            itemCatalogo: itemCat,
            precioNormalizado: calcularPrecioNormalizado({ nombre: nombreEncontrado, precio: resultado.precio, precioStr: resultado.precioStr })
        };
    }

    // 3. Validación de CATEGORÍA E INCOMPATIBILIDADES (Aplica a TODAS las categorías)
    if (intencion.categoria && DEFINICION_CATEGORIAS[intencion.categoria]) {
        var defCat = DEFINICION_CATEGORIAS[intencion.categoria];

        // Función auxiliar para coincidencia exacta de palabra en términos cortos (evita falsos positivos como 'te' dentro de 'mate')
        function contienePalabra(texto, palabra) {
            if (!texto || !palabra) return false;
            if (palabra.length <= 4) {
                var rx = new RegExp('(?:^|\\s)' + palabra.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') + '(?:$|\\s)', 'i');
                return rx.test(texto);
            }
            return texto.includes(palabra);
        }

        // A) Rechazo estricto si contiene términos incompatibles
        if (defCat.incompatibles) {
            for (var k = 0; k < defCat.incompatibles.length; k++) {
                var inc = defCat.incompatibles[k];
                if (contienePalabra(nombreNorm, inc)) {
                    return {
                        estado: 'COINCIDENCIA NO VÁLIDA',
                        valido: false,
                        motivo: 'El producto devuelto (' + nombreEncontrado + ') contiene "' + inc.toUpperCase() + '", incompatible con la categoría requerida (' + intencion.categoria.toUpperCase() + ').',
                        intencion: intencion.tipo,
                        marca: intencion.marca
                    };
                }
            }
        }

        // B) Debe contener al menos un término válido de la categoría
        if (defCat.terminos) {
            var coincideCategoria = defCat.terminos.some(function(t) {
                return contienePalabra(nombreNorm, t);
            });
            if (!coincideCategoria) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'El producto devuelto (' + nombreEncontrado + ') no pertenece a la categoría ' + intencion.categoria.toUpperCase() + '.',
                    intencion: intencion.tipo,
                    marca: intencion.marca
                };
            }
        }
    }

    // 4. Validación de BÚSQUEDA GENÉRICA
    if (intencion.tipo === 'GENERICA') {
        // Verificar si se buscó un sabor o variante descriptiva específica
        var saboresArray = Array.from(SABORES_Y_VARIANTES);
        for (var s = 0; s < saboresArray.length; s++) {
            var sab = saboresArray[s];
            if (intencion.queryNormalizada.includes(sab) && !nombreNorm.includes(sab)) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'Se solicitó variante/sabor "' + sab + '" pero el producto devuelto (' + nombreEncontrado + ') no lo incluye.',
                    intencion: intencion.tipo,
                    marca: null
                };
            }
        }

        return {
            estado: 'VALIDADA',
            valido: true,
            motivo: 'Coincidencia genérica validada (alternativa comercial aceptable).',
            intencion: intencion.tipo,
            marca: null
        };
    }

    // 5. Validación de BÚSQUEDA ESPECÍFICA (MARCA Y CALIFICADORES)
    if (intencion.marca) {
        var marcaBuscada = intencion.marca;
        var palabrasMarca = marcaBuscada.split(/\s+/).filter(function(w) {
            return !STOP_WORDS.has(w);
        });
        var coincideMarca = palabrasMarca.every(function(m) {
            if (m === 'lucchetti' || m === 'luchetti') {
                return nombreNorm.includes('lucchetti') || nombreNorm.includes('luchetti');
            }
            var regexM = new RegExp('(?:^|\\s)' + m.replace('-', '[-\\s]') + '(?:$|\\s)', 'i');
            return regexM.test(nombreNorm) || nombreNorm.includes(m);
        });
        if (!coincideMarca) {
            return {
                estado: 'COINCIDENCIA NO VÁLIDA',
                valido: false,
                motivo: 'Marca requerida "' + marcaBuscada.toUpperCase() + '" no coincide con el producto devuelto ("' + nombreEncontrado + '").',
                intencion: intencion.tipo,
                marca: intencion.marca
            };
        }
    }

    // Validación de Sabor o Variante específica en búsqueda específica
    var variantesArray = Array.from(SABORES_Y_VARIANTES);
    for (var v = 0; v < variantesArray.length; v++) {
        var varItem = variantesArray[v];
        if (intencion.queryNormalizada.includes(varItem)) {
            var coincideVar = nombreNorm.includes(varItem);
            if (!coincideVar && (varItem === 'tallarin' || varItem === 'tallarines')) {
                coincideVar = nombreNorm.includes('tallarin') || nombreNorm.includes('tallarines');
            }
            if (!coincideVar) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'Variante/sabor "' + varItem + '" no presente en el resultado encontrado.',
                    intencion: intencion.tipo,
                    marca: intencion.marca
                };
            }
        }
    }

    // Validación de línea específica (ej: "zero", "light", "parboil", "oro", "clasica")
    for (var li = 0; li < LINEAS_PRODUCTO.length; li++) {
        var lineaProd = LINEAS_PRODUCTO[li];
        var rxL = new RegExp('(?:^|\\s)' + lineaProd + '(?:$|\\s)', 'i');
        if (rxL.test(intencion.queryNormalizada)) {
            // Excepción: para yerba mate, 'tradicional' y 'suave' / 'con palo' son equivalentes a nivel de línea base
            if (intencion.categoria === 'yerba' && lineaProd === 'tradicional' && (nombreNorm.includes('suave') || nombreNorm.includes('con palo'))) {
                continue;
            }
            if (intencion.categoria === 'yerba' && lineaProd === 'suave' && (nombreNorm.includes('tradicional') || nombreNorm.includes('con palo'))) {
                continue;
            }
            // Excepción: para leche, 'entera' y 'clasica' / '3%' son equivalentes a nivel de línea estándar
            if (intencion.categoria === 'leche' && (lineaProd === 'clasica' || lineaProd === 'entera') && (nombreNorm.includes('clasica') || nombreNorm.includes('entera') || nombreNorm.includes('3%'))) {
                continue;
            }
            if (!rxL.test(nombreNorm)) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'Se solicitó la línea específica "' + lineaProd.toUpperCase() + '" pero el producto devuelto (' + nombreEncontrado + ') no la incluye.',
                    intencion: intencion.tipo,
                    marca: intencion.marca
                };
            }
        }
    }

    // Validación de Presentación / Tamaño si se especificó (Tolerancia CERO a presentaciones distintas)
    if (intencion.presentacion) {
        var presEncontrada = extraerPresentacion(nombreEncontrado);
        if (presEncontrada) {
            if (presEncontrada.tipo !== intencion.presentacion.tipo || Math.abs(presEncontrada.valor - intencion.presentacion.valor) > 0.001) {
                return {
                    estado: 'COINCIDENCIA NO VÁLIDA',
                    valido: false,
                    motivo: 'Presentación incompatible: solicitada ' + intencion.presentacion.raw + ' vs encontrada ' + presEncontrada.raw + '.',
                    intencion: intencion.tipo,
                    marca: intencion.marca
                };
            }
        }
    }

    return {
        estado: 'VALIDADA',
        valido: true,
        motivo: 'Coincidencia específica validada (marca, categoría y atributos conformes).',
        intencion: intencion.tipo,
        marca: intencion.marca,
        precioNormalizado: calcularPrecioNormalizado({ nombre: nombreEncontrado, precio: resultado.precio, precioStr: resultado.precioStr })
    };
}

// ==============================================================================
// REGLA DE LOS 3 SUPERMERCADOS:
// Compara y valida que la misma marca, variante y presentación existan en los 3
// ==============================================================================
function validarComparacion3Supermercados(itemsDelProd) {
    var supers = ['Carrefour', 'COTO', 'Día %'];
    var presentes = [];
    var faltantes = [];

    if (!Array.isArray(itemsDelProd) || itemsDelProd.length === 0) {
        return {
            comparable: false,
            motivo: 'No hay datos registrados para este producto.',
            supermercadosPresentes: [],
            supermercadosFaltantes: supers
        };
    }

    supers.forEach(function(s) {
        var found = itemsDelProd.filter(function(x) { return x.supermercado === s; }).pop();
        if (found && found.valido && found.precio !== null && found.precio > 0 && (found.stock_status === 'DISPONIBLE' || found.stockRaw === 'DISPONIBLE')) {
            presentes.push(s);
        } else {
            faltantes.push(s);
        }
    });

    if (faltantes.length > 0) {
        return {
            comparable: false,
            disponibles: presentes.length,
            motivo: 'Incompleto: no disponible en los 3 supermercados (falta o no válido en ' + faltantes.join(', ') + ').',
            supermercadosPresentes: presentes,
            supermercadosFaltantes: faltantes
        };
    }

    // Comprobar que las presentaciones entre los tres supermercados sean idénticas
    var validos = supers.map(function(s) {
        return itemsDelProd.filter(function(x) { return x.supermercado === s; }).pop();
    });
    var pres0 = extraerPresentacion(validos[0].nombre || validos[0].nombre_encontrado || '');
    for (var i = 1; i < validos.length; i++) {
        var presI = extraerPresentacion(validos[i].nombre || validos[i].nombre_encontrado || '');
        if (pres0 && presI) {
            if (pres0.tipo !== presI.tipo || Math.abs(pres0.valor - presI.valor) > 0.001) {
                return {
                    comparable: false,
                    disponibles: presentes.length,
                    motivo: 'Presentación discrepante entre supermercados (' + pres0.raw + ' vs ' + presI.raw + ').',
                    supermercadosPresentes: presentes,
                    supermercadosFaltantes: []
                };
            }
        }
    }

    // Calcular precio mínimo y ganador entre los 3
    var minP = Infinity;
    var gan = null;
    validos.forEach(function(v) {
        if (v && v.precio !== null && v.precio < minP) {
            minP = v.precio;
            gan = v.supermercado;
        }
    });

    return {
        comparable: true,
        disponibles: presentes.length,
        precioMinimo: minP !== Infinity ? minP : null,
        supermercadoGanador: gan,
        motivo: 'Producto válido y disponible en los 3 supermercados con la misma presentación.',
        supermercadosPresentes: presentes,
        supermercadosFaltantes: []
    };
}

// Parsea cadenas de precios argentinos (ej: "$ 5.209,00 c/u" -> 5209.00)
function parsePrecio(str) {
    if (!str || typeof str !== 'string' || str === 'N/D' || str === 'null') return null;
    var match = str.match(/[\d.]+(?:,\d+)?/);
    if (!match) return null;
    var raw = match[0].replace(/\./g, '').replace(',', '.');
    var val = parseFloat(raw);
    return isNaN(val) || val <= 0 ? null : val;
}

// Formatea número como moneda argentina ($ 1.234,56)
function formatoMoneda(num) {
    if (num === null || num === undefined || isNaN(num)) return 'N/D';
    return '$ ' + num.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Lee resultados.csv reconociendo formatos de 8 o 5 columnas
function leerResultadosCSV(filePath) {
    const fs = require('fs');
    const path = require('path');
    var csvFile = filePath || path.join(__dirname, 'resultados.csv');
    if (!fs.existsSync(csvFile)) return [];

    var raw = fs.readFileSync(csvFile, 'utf-8');
    var lines = raw.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });
    if (lines.length <= 1) return [];

    var items = [];
    for (var i = 1; i < lines.length; i++) {
        var line = lines[i];
        if (line.startsWith('sep=')) continue;

        // Parsear fila CSV respetando comillas
        var match = line.match(/(?:^|,)(?:"([^"]*)"|([^,]*))/g);
        if (!match) continue;
        var cols = match.map(function(c) {
            c = c.replace(/^,/, '').trim();
            if (c.startsWith('"') && c.endsWith('"')) c = c.slice(1, -1);
            return c;
        });

        if (cols.length >= 8) {
            // Formato nuevo de 8 a 10 columnas:
            // modo, producto_solicitado, nombre_encontrado, precio, supermercado, url, fecha, stock_status, cantidad, unidad
            items.push({
                modo: cols[0] || 'compra_mes',
                producto: cols[1] || 'producto',
                nombre: cols[2] || 'N/D',
                precioStr: cols[3] || 'N/D',
                precio: parsePrecio(cols[3]),
                supermercado: cols[4] || 'N/D',
                url: cols[5] || '',
                fecha: cols[6] || '',
                stockRaw: cols[7] || 'DISPONIBLE',
                cantidad: cols[8] ? (parseFloat(String(cols[8]).replace(',', '.')) || 1) : 1,
                unidad: cols[9] || ''
            });
        } else if (cols.length >= 5) {
            // Formato antiguo de 5 columnas: Nombre, Precio, Supermercado, URL, Fecha
            var nombre = cols[0] || 'N/D';
            var precioStr = cols[1] || 'N/D';
            var superm = cols[2] || 'N/D';
            var url = cols[3] || '';
            var fecha = cols[4] || '';

            items.push({
                modo: 'compra_mes',
                producto: nombre.split(/\s+/).slice(0, 2).join(' '),
                nombre: nombre,
                precioStr: precioStr,
                precio: parsePrecio(precioStr),
                supermercado: superm,
                url: url,
                fecha: fecha,
                stockRaw: 'DISPONIBLE'
            });
        }
    }
    return items;
}

// Genera y muestra en consola el reporte para Búsqueda Individual
function mostrarReporteIndividual(productoBuscado) {
    const path = require('path');
    var items = leerResultadosCSV(path.join(__dirname, 'resultados.csv'));
    if (items.length === 0) {
        console.log('[ERROR] No se encontraron resultados registrados en resultados.csv');
        return;
    }

    // Filtrar por modo individual o tomar los últimos registros
    var individuales = items.filter(function(x) { return x.modo === 'individual'; });
    var grupo = [];

    if (productoBuscado) {
        var pNorm = normalizar(productoBuscado);
        grupo = individuales.filter(function(x) { return normalizar(x.producto) === pNorm; });
        if (grupo.length === 0) {
            // Si no coincide exactamente por modo individual, buscar en los últimos items
            grupo = items.filter(function(x) { return normalizar(x.producto) === pNorm; });
        }
    }

    // Si aún no hay grupo, tomar los últimos 3 registros
    if (grupo.length === 0) {
        grupo = items.slice(-3);
    } else if (grupo.length > 3) {
        // Tomar los últimos 3 de esa búsqueda
        grupo = grupo.slice(-3);
    }

    var queryFinal = productoBuscado || (grupo[0] ? grupo[0].producto : 'Producto');
    var intencion = detectarIntencion(queryFinal);

    // Validar cada resultado del grupo
    var evaluados = grupo.map(function(item) {
        var v = validarCoincidencia(queryFinal, item);
        return {
            supermercado: item.supermercado,
            nombre: item.nombre,
            precio: item.precio,
            precioStr: item.precioStr,
            estado: v.estado,
            valido: v.valido,
            motivo: v.motivo,
            url: item.url
        };
    });

    // Encontrar opciones válidas con precio disponible
    var validos = evaluados.filter(function(e) { return e.valido && e.precio !== null; });
    validos.sort(function(a, b) { return a.precio - b.precio; });

    var ganador = validos.length > 0 ? validos[0] : null;
    var masCaro = validos.length > 1 ? validos[validos.length - 1] : null;
    var ahorro = (ganador && masCaro && masCaro.precio > ganador.precio) ? (masCaro.precio - ganador.precio) : 0;
    var ahorroPct = (masCaro && masCaro.precio > 0) ? ((ahorro / masCaro.precio) * 100) : 0;

    // Impresión en consola con formato prolijo
    console.log('\n================================================================================');
    console.log('       🔍 REPORTE DE BÚSQUEDA INDIVIDUAL - VALIDACIÓN INTELIGENTE');
    console.log('================================================================================');
    console.log(' Producto Solicitado : "' + queryFinal + '"');
    console.log(' Intención Detectada : ' + intencion.tipo + (intencion.marca ? ' (Marca: ' + intencion.marca.toUpperCase() + ')' : '') + (intencion.categoria ? ' [Categoría: ' + intencion.categoria + ']' : ''));
    console.log(' Regla Aplicada      : ' + (intencion.tipo === 'ESPECIFICA' ? 'Validación ESTRICTA de marca y tipo (rechaza sustitutos)' : 'Comparación abierta de alternativas de mercado'));
    console.log('--------------------------------------------------------------------------------');
    console.log(
        ' SUPERMERCADO'.padEnd(15) + '│ ' +
        'PRECIO'.padEnd(14) + '│ ' +
        'ESTADO'.padEnd(23) + '│ ' +
        'PRODUCTO ENCONTRADO'
    );
    console.log('─'.repeat(15) + '┼─' + '─'.repeat(13) + '┼─' + '─'.repeat(22) + '┼─' + '─'.repeat(25));

    evaluados.forEach(function(e) {
        var esGanador = ganador && e.supermercado === ganador.supermercado && e.valido;
        var tagEstado = esGanador ? '🏆 GANADOR' : (e.valido ? ' VALIDADA' : '❌ ' + e.estado);
        var precioTexto = e.precio !== null ? formatoMoneda(e.precio) : (e.precioStr || 'N/D');
        var nombreTexto = e.nombre.length > 45 ? e.nombre.slice(0, 42) + '...' : e.nombre;

        console.log(
            (' ' + e.supermercado).padEnd(15) + '│ ' +
            precioTexto.padEnd(14) + '│ ' +
            tagEstado.padEnd(23) + '│ ' +
            nombreTexto
        );
        if (!e.valido && e.motivo) {
            console.log(' '.repeat(15) + '│ ' + ' '.repeat(13) + '│ ' + ('   └─ Motivo: ' + e.motivo).slice(0, 60));
        }
    });

    console.log('--------------------------------------------------------------------------------');
    if (ganador) {
        console.log(' 🏆 MEJOR OPCIÓN     : ' + ganador.supermercado + ' (' + formatoMoneda(ganador.precio) + ')');
        if (ahorro > 0) {
            console.log(' 💰 AHORRO POTENCIAL : ' + formatoMoneda(ahorro) + ' (' + ahorroPct.toFixed(0) + '% menos que ' + masCaro.supermercado + ')');
        } else if (validos.length === 1) {
            console.log(' ℹ️  DISPONIBILIDAD   : Solo ' + ganador.supermercado + ' tuvo el producto con coincidencia válida.');
        } else {
            console.log(' ℹ️  PRECIOS         : Mismo valor en las opciones validadas.');
        }
    } else {
        console.log(' ⚠️  ALERTA: Ningún supermercado arrojó una coincidencia válida disponible.');
        console.log('     El sistema evitó sustituir con productos erróneos (marcas ajenas, frutas o shampoo).');
    }
    console.log('================================================================================\n');
}

// Limpia resultados según la opción seleccionada sin tocar input.csv
function limpiarResultados(opcion) {
    const fs = require('fs');
    const path = require('path');
    var csvFile = path.join(__dirname, 'resultados.csv');
    var header = 'modo,producto_solicitado,nombre_encontrado,precio,supermercado,url,fecha,stock_status,cantidad,unidad\n';

    if (!fs.existsSync(csvFile)) {
        fs.writeFileSync(csvFile, header, 'utf-8');
        console.log('[OK] Archivo resultados.csv inicializado.');
        return;
    }

    var items = leerResultadosCSV(csvFile);

    if (opcion === '1') {
        // Limpiar solo compra del mes actual, conservar búsquedas individuales
        var restantes = items.filter(function(x) { return x.modo === 'individual'; });
        var contenido = header;
        restantes.forEach(function(r) {
            var nomEsc = r.nombre.includes(',') ? '"' + r.nombre + '"' : r.nombre;
            var preEsc = r.precioStr.includes(',') ? '"' + r.precioStr + '"' : r.precioStr;
            contenido += [r.modo, r.producto, nomEsc, preEsc, r.supermercado, r.url, r.fecha, r.stockRaw, r.cantidad || 1, r.unidad || ''].join(',') + '\n';
        });
        fs.writeFileSync(csvFile, contenido, 'utf-8');
        console.log('[OK] Se eliminaron los registros de "Compra del mes". Se conservó el historial de consultas individuales.');
    } else if (opcion === '2') {
        // Limpiar solo historial de consultas individuales, conservar compra del mes
        var restantesM = items.filter(function(x) { return x.modo !== 'individual'; });
        var contenidoM = header;
        restantesM.forEach(function(r) {
            var nomEscM = r.nombre.includes(',') ? '"' + r.nombre + '"' : r.nombre;
            var preEscM = r.precioStr.includes(',') ? '"' + r.precioStr + '"' : r.precioStr;
            contenidoM += [r.modo, r.producto, nomEscM, preEscM, r.supermercado, r.url, r.fecha, r.stockRaw, r.cantidad || 1, r.unidad || ''].join(',') + '\n';
        });
        fs.writeFileSync(csvFile, contenidoM, 'utf-8');
        console.log('[OK] Se limpió el historial de búsquedas individuales. Se conservó la compra del mes.');
    } else if (opcion === '3') {
        // Limpiar todo
        fs.writeFileSync(csvFile, header, 'utf-8');
        console.log('[OK] Todo el archivo resultados.csv ha sido reiniciado con cabeceras limpias.');
    } else {
        console.log('[INFO] Operación de limpieza cancelada.');
    }
}

// Genera temp_input.csv de forma 100% segura respetando RFC-4180 exclusivamente para productos del catálogo
function crearTempInput(producto, cantidad, unidad) {
    const fs = require('fs');
    const path = require('path');
    const catEngine = require('./catalogo.js');

    // Limpiar consultas individuales previas para que cada búsqueda sea limpia y actualice a la nueva
    limpiarResultados('2');

    // Validación estricta contra catálogo cerrado
    const val = catEngine.validarEntrada({ producto, cantidad, unidad });
    if (!val.valido || !val.item) {
        throw new Error(`El producto "${producto}" no pertenece al catálogo cerrado oficial.`);
    }

    const itemCat = val.item;
    const prodOficial = itemCat.nombre_completo || itemCat.producto;
    const cantOficial = itemCat.cantidad;
    const unidOficial = itemCat.unidad;
    let termBusqueda = itemCat.termino_busqueda || prodOficial;

    // Adaptaciones específicas para búsqueda individual con TagUI
    const pLow = (prodOficial + ' ' + (producto || '')).toLowerCase();
    if (pLow.includes('coca cola') || pLow.includes('coca-cola')) {
        termBusqueda = 'coca cola 2,25L';
    } else if (pLow.includes('sprite')) {
        termBusqueda = 'sprite 2,25L';
    } else if (pLow.includes('manaos') && pLow.includes('naranja')) {
        termBusqueda = 'manaos naranja';
    } else if (pLow.includes('manaos') && (pLow.includes('lima') || pLow.includes('limon'))) {
        termBusqueda = 'manaos lima limon';
    } else if (pLow.includes('manaos') && pLow.includes('cola')) {
        termBusqueda = 'manaos cola';
    }

    var tempFile = path.join(__dirname, 'temp_input.csv');
    var escProd = '"' + prodOficial.replace(/"/g, '""') + '"';
    var escUnid = '"' + unidOficial.replace(/"/g, '""') + '"';
    var escTerm = '"' + termBusqueda.replace(/"/g, '""') + '"';

    fs.writeFileSync(tempFile, 'producto,modo,cantidad,unidad,termino\r\n' + escProd + ',individual,' + cantOficial + ',' + escUnid + ',' + escTerm + '\r\n', 'utf8');
    console.log('[OK] temp_input.csv generado de forma segura para: ' + prodOficial);
    return tempFile;
}

// Ejecución como script CLI
if (require.main === module) {
    var args = process.argv.slice(2);
    if (args[0] === '--crear-temp') {
        var prodArg = args.slice(1).join(' ').trim();
        try {
            crearTempInput(prodArg);
        } catch (e) {
            console.error('[ERROR]', e.message);
            process.exit(1);
        }
    } else if (args[0] === '--reporte-individual') {
        var queryArg = args.slice(1).join(' ').trim();
        mostrarReporteIndividual(queryArg || null);
    } else if (args[0] === '--limpiar') {
        limpiarResultados(args[1] || '3');
    } else if (args[0] === '--test' || args[0] === '--diagnostico') {
        console.log('======================================================================');
        console.log('       🧪 BATERÍA DE PRUEBAS UNITARIAS: validador.js');
        console.log('======================================================================');
        var errores = 0;

        function assertEq(desc, real, esperado) {
            if (real === esperado) {
                console.log(' [OK] ' + desc + ' -> ' + real);
            } else {
                console.log(' [FAIL] ' + desc + ' -> Esperado: ' + esperado + ', Obtenido: ' + real);
                errores++;
            }
        }

        // Test 1: Rechazo de Pepsi para Manaos Cola específico
        var r1 = validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa Pepsi Cola 2.25L', precio: 1000 });
        assertEq('Rechazo de Pepsi para consulta Manaos Cola', r1.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 2: Rechazo de Coca Cola para Manaos Cola específico
        var r2 = validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa Coca Cola 2.25L', precio: 2200 });
        assertEq('Rechazo de Coca Cola para consulta Manaos Cola', r2.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 3: Rechazo de Fanta para Manaos Cola específico
        var r3 = validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa Fanta Pomelo 2L', precio: 1500 });
        assertEq('Rechazo de Fanta para consulta Manaos Cola', r3.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 4: Rechazo de fruta por kg para bebida
        var r4 = validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Naranja . Xkg', precio: 999 });
        assertEq('Rechazo de fruta para Manaos Cola', r4.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 5: Aceptación de alternativa en búsqueda genérica
        var r5 = validarCoincidencia('gaseosa cola', { nombre: 'Gaseosa Manaos Cola 2.25L', precio: 1000 });
        assertEq('Aceptación de alternativa en búsqueda genérica', r5.estado, 'VALIDADA');

        // Test 6: Equivalencia 2.25L vs 2250ml
        var r6 = validarCoincidencia('Coca Cola 2.25L', { nombre: 'Coca Cola 2250ml', precio: 2000 });
        assertEq('Equivalencia 2.25L vs 2250ml', r6.estado, 'VALIDADA');

        // Test 7: Equivalencia 2,25 litros vs 2.25L
        var r7 = validarCoincidencia('Coca Cola 2,25 litros', { nombre: 'Coca Cola 2.25L', precio: 2000 });
        assertEq('Equivalencia 2,25 litros vs 2.25L', r7.estado, 'VALIDADA');

        // Test 8: Incompatibilidad 2.25L vs 500ml (ratio fuera de tolerancia)
        var r8 = validarCoincidencia('Coca Cola 2.25L', { nombre: 'Coca Cola 500ml', precio: 800 });
        assertEq('Incompatibilidad 2.25L vs 500ml', r8.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 9: Rechazo estricto de presentación incompatible (1kg vs 500g)
        var r9 = validarCoincidencia('Arroz Ala 1kg', { nombre: 'Arroz Ala 500g', precio: 800 });
        assertEq('Rechazo estricto de presentación 1kg vs 500g', r9.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 10: Producto sin stock
        var r10 = validarCoincidencia('leche', { nombre: 'Leche Serenisima 1L', precioStr: 'Sin stock', stockRaw: 'SIN STOCK' });
        assertEq('Detección de Sin Stock', r10.estado, 'SIN STOCK');

        // Test 11: Generalización - Rechazo de alfajor o jugo cuando se busca leche
        var r11 = validarCoincidencia('leche baggio', { nombre: 'Alfajor Havanna Chocolate', precio: 1500 });
        assertEq('Generalización: Rechazo de Alfajor para Leche', r11.estado, 'COINCIDENCIA NO VÁLIDA');

        var r11b = validarCoincidencia('leche baggio', { nombre: 'Jugo Baggio Naranja 1L', precio: 1200 });
        assertEq('Generalización: Rechazo de Jugo para Leche', r11b.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 12: Generalización - Rechazo de fideos cuando se busca arroz
        var r12 = validarCoincidencia('arroz gallo', { nombre: 'Fideos Tallarín Matarazzo 500g', precio: 1400 });
        assertEq('Generalización: Rechazo de Fideos para Arroz', r12.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 13: Generalización - Rechazo de otra marca cuando se pide marca específica
        var r13 = validarCoincidencia('arroz gallo', { nombre: 'Arroz Molinos Ala Largo Fino 1kg', precio: 1900 });
        assertEq('Generalización: Rechazo de marca distinta para Arroz Gallo', r13.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 14: Generalización - Rechazo de vinagre para aceite
        var r14 = validarCoincidencia('aceite natura', { nombre: 'Vinagre de Alcohol Menoyo 1L', precio: 1100 });
        assertEq('Generalización: Rechazo de Vinagre para Aceite', r14.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 15: Generalización - Aceptación correcta de marca y categoría en cualquier producto
        var r15 = validarCoincidencia('fideos matarazzo', { nombre: 'Fideos Tirabuzón Matarazzo 500g', precio: 1800 });
        assertEq('Generalización: Aceptación Fideos Matarazzo', r15.estado, 'VALIDADA');

        var r16 = validarCoincidencia('detergente magistral', { nombre: 'Detergente Magistral Limón 500ml', precio: 2200 });
        assertEq('Generalización: Aceptación Detergente Magistral', r16.estado, 'VALIDADA');

        var r17 = validarCoincidencia('yerba playadito', { nombre: 'Yerba Mate Playadito 1kg', precio: 4500 });
        assertEq('Generalización: Aceptación Yerba Playadito', r17.estado, 'VALIDADA');

        // Test 18: Equivalencia General - Detección y rechazo de accesorios (vaso vs gaseosa)
        var r18 = validarCoincidencia('coca cola', { nombre: 'Vaso de Vidrio Coca Cola Original', precio: 3500 });
        assertEq('Equivalencia General: Rechazo de Accesorio (Vaso)', r18.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 19: Equivalencia General - Rechazo de línea incompatible (Zero vs Común)
        var r19 = validarCoincidencia('coca cola zero', { nombre: 'Gaseosa Coca Cola Sabor Original 2.25L', precio: 3800 });
        assertEq('Equivalencia General: Rechazo de Línea distinta (Original para Zero)', r19.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 20: Equivalencia General - Normalización de precio por kg
        var normKg = calcularPrecioNormalizado({ nombre: 'Arroz Ala 500g', precio: 1500 });
        assertEq('Equivalencia General: Normalización Precio por kg (500g -> 1kg)', normKg.precioNormalizado, 3000);

        // Test 21: Equivalencia General - Normalización de precio por litro
        var normLt = calcularPrecioNormalizado({ nombre: 'Leche La Serenisima 1L', precio: 1400 });
        assertEq('Equivalencia General: Normalización Precio por litro (1L)', normLt.precioNormalizado, 1400);

        // Test 22: Equivalencia General - Comparabilidad entre marcas en búsqueda genérica
        var compGen = sonComparables('Arroz Gallo Oro 1kg', 'Arroz Molinos Ala 1kg', 'arroz');
        assertEq('Equivalencia General: Comparabilidad entre marcas en búsqueda genérica', compGen.comparable, true);

        // Test 23: Equivalencia General - Rechazo de comparabilidad cuando se busca marca específica
        var compMarca = sonComparables('Arroz Gallo Oro 1kg', 'Arroz Molinos Ala 1kg', 'arroz gallo');
        assertEq('Equivalencia General: Rechazo comparabilidad marca distinta', compMarca.comparable, false);

        // Test 24: Equivalencia General - Extracción de atributos de producto
        var attrTest = extraerAtributos('Gaseosa Coca Cola Zero 2.25L');
        assertEq('Equivalencia General: Atributo Marca', attrTest.marca, 'coca cola');
        assertEq('Equivalencia General: Atributo Línea', attrTest.linea, 'zero');
        assertEq('Equivalencia General: Atributo Presentación Litros', attrTest.presentacion.valor, 2.25);

        // ====================================================================
        // TESTS DEL CATÁLOGO CERRADO Y REGLAS ESTRICTAS DE CÁTEDRA
        // ====================================================================
        // Test 25: Aceptación Coca Cola 2.25 L
        var t25 = validarCoincidencia('Coca Cola 2.25L', { nombre: 'Gaseosa Coca Cola Sabor Original 2.25 L', precio: 3800 });
        assertEq('Catálogo: Aceptación Coca Cola 2.25 L', t25.estado, 'VALIDADA');

        // Test 26: Aceptación Sprite 2.25 L
        var t26 = validarCoincidencia('Sprite 2.25L', { nombre: 'Gaseosa Sprite Lima Limon 2.25 L', precio: 3600 });
        assertEq('Catálogo: Aceptación Sprite 2.25 L', t26.estado, 'VALIDADA');

        // Test 27: Aceptación Manaos Cola 2.25 L
        var t27 = validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa cola Manaos 2,25 lts', precio: 1500 });
        assertEq('Catálogo: Aceptación Manaos Cola 2.25 L', t27.estado, 'VALIDADA');

        // Test 27b: Aceptación Manaos Naranja 2.25 L
        var t27b = validarCoincidencia('Manaos Naranja 2.25L', { nombre: 'Gaseosa Naranja Manaos 2.25l', precio: 1500 });
        assertEq('Catálogo: Aceptación Manaos Naranja 2.25 L', t27b.estado, 'VALIDADA');

        // Test 27c: Aceptación Manaos Lima Limón 2.25 L
        var t27c = validarCoincidencia('Manaos Lima Limon 2.25L', { nombre: 'Gaseosa lima limón Manaos 2,25 lts', precio: 1500 });
        assertEq('Catálogo: Aceptación Manaos Lima Limón 2.25 L', t27c.estado, 'VALIDADA');

        // Test 28: Aceptación Arroz Gallo 1 kg
        var t28 = validarCoincidencia('Arroz Gallo 1kg', { nombre: 'Arroz Gallo Largo Fino 1 kg', precio: 2200 });
        assertEq('Catálogo: Aceptación Arroz Gallo 1 kg', t28.estado, 'VALIDADA');

        // Test 29: Aceptación Leche La Serenisima 1 L
        var t29 = validarCoincidencia('Leche La Serenisima 1L', { nombre: 'Leche La Serenísima Entera Clásica 1 L', precio: 1450 });
        assertEq('Catálogo: Aceptación Leche La Serenísima 1 L', t29.estado, 'VALIDADA');

        // Test 30: RECHAZO Manaos Cola vs Manaos Naranja 2.25 L
        var t30 = validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa Naranja Manaos 2.25l', precio: 1200 });
        assertEq('Catálogo: Rechazo Manaos Cola vs Manaos Naranja', t30.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 31: RECHAZO Manaos Cola vs Manaos Lima Limón 2.25 L
        var t31 = validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa lima limón Manaos 2,25 lts', precio: 1500 });
        assertEq('Catálogo: Rechazo Manaos Cola vs Manaos Lima Limón', t31.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 32: RECHAZO Manaos Cola 2.25 L vs Manaos Cola 1.5 L
        var t32 = validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa Cola Manaos 1.5 L', precio: 1100 });
        assertEq('Catálogo: Rechazo Manaos Cola 2.25 L vs 1.5 L', t32.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 33: RECHAZO Arroz Gallo 1 kg vs Arroz Gallo 500 g
        var t33 = validarCoincidencia('Arroz Gallo 1kg', { nombre: 'Arroz Gallo 500 g', precio: 1200 });
        assertEq('Catálogo: Rechazo Arroz Gallo 1 kg vs 500 g', t33.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 33b: RECHAZO Bebida Vegetal para Leche La Serenísima
        var t33b = validarCoincidencia('Leche La Serenísima', { nombre: 'Bebida Vegetal Almendra La Serenisima Sin Endulzar 1 Lt.', precio: 5159, cantidad: 1, unidad: 'L' });
        assertEq('Catálogo: Rechazo Bebida Vegetal para Leche La Serenísima', t33b.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 33c: RECHAZO Leche Protein para Leche La Serenísima Clásica
        var t33c = validarCoincidencia('Leche La Serenísima', { nombre: 'Leche Protein La Serenisima 1L', precio: 2340, cantidad: 1, unidad: 'L' });
        assertEq('Catálogo: Rechazo Leche Protein para Leche Clásica', t33c.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 33d: ACEPTACIÓN Leche La Serenísima Clásica 3% 1L (Carrefour / Día)
        var t33d = validarCoincidencia('Leche La Serenísima', { nombre: 'Leche La serenisima clásica 3% 1L', precio: 2915, cantidad: 1, unidad: 'L' });
        assertEq('Catálogo: Aceptación Leche La Serenísima Clásica 3% 1L', t33d.estado, 'VALIDADA');

        // Test 33e: ACEPTACIÓN Galletitas Criollitas 100 g. x 3 uni (Pack Día % / Carrefour)
        var t33e = validarCoincidencia('Galletitas Criollitas', { nombre: 'Galletitas original Criollitas 100 g. x 3 uni', precio: 1979 });
        assertEq('Catálogo: Aceptación Criollitas 100 g. x 3 uni (300g)', t33e.estado, 'VALIDADA');

        // Test 33f: ACEPTACIÓN Galletitas Criollitas 3x 100gramos (Pack 3x)
        var t33f = validarCoincidencia('Galletitas Criollitas', { nombre: 'Galletitas Criollitas 3x 100gramos', precio: 1979 });
        assertEq('Catálogo: Aceptación Criollitas 3x 100gramos (300g)', t33f.estado, 'VALIDADA');

        // Test 33g: RECHAZO Galletitas Criollitas 100 g individual (no es pack de 300g)
        var t33g = validarCoincidencia('Galletitas Criollitas', { nombre: 'Galletitas Criollitas 100 g', precio: 700 });
        assertEq('Catálogo: Rechazo Criollitas 100 g individual vs 300 g', t33g.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 33h: ACEPTACIÓN Papel Higiénico Higienol Max (Carrefour, COTO y Día %)
        var t33h_carrefour = validarCoincidencia('Papel Higiénico Higienol Max', { nombre: 'Papel higiénico Higienol Max hoja simple 100 mts 4 uni', precio: 7680 });
        assertEq('Catálogo: Aceptación Higienol Max Carrefour', t33h_carrefour.estado, 'VALIDADA');

        var t33h_coto = validarCoincidencia('Papel Higiénico Higienol Max', { nombre: 'Papel Higiénico HIGIENOL Max Hoja Simple 100 M 4 Un', precio: 5759.99 });
        assertEq('Catálogo: Aceptación Higienol Max COTO', t33h_coto.estado, 'VALIDADA');

        var t33h_dia = validarCoincidencia('Papel Higiénico Higienol Max', { nombre: 'Papel Higiénico Higienol Max hoja simple 100 m 4 Ud.', precio: 7680 });
        assertEq('Catálogo: Aceptación Higienol Max Día %', t33h_dia.estado, 'VALIDADA');

        // Test 33i: RECHAZO Papel Higiénico Higienol Fresh 30 mts cuando se busca Max (100m)
        var t33i = validarCoincidencia('Papel Higiénico Higienol Max', { nombre: 'Papel higiénico Higienol Fresh hoja simple 30 mts 4 uni', precio: 2499 });
        assertEq('Catálogo: Rechazo Higienol Fresh 30m vs Max', t33i.estado, 'COINCIDENCIA NO VÁLIDA');

        // Test 33j: ACEPTACIÓN Papel Higiénico Higienol Max para consulta general Papel Higiénico Higienol
        var t33j = validarCoincidencia('Papel Higiénico Higienol', { nombre: 'Papel higiénico Higienol Max hoja simple 100 mts 4 uni', precio: 7680 });
        assertEq('Catálogo: Aceptación Higienol Max para búsqueda Higienol', t33j.estado, 'VALIDADA');

        // Test 34: Comparación de 3 Supermercados (Incompleto en Día %)
        var itemsTestIncompleto = [
            { supermercado: 'Carrefour', valido: true, precio: 1500, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25 L' },
            { supermercado: 'COTO', valido: true, precio: 1550, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25 L' },
            { supermercado: 'Día %', valido: false, precio: null, stock_status: 'NO ENCONTRADO', nombre: 'No encontrado' }
        ];
        var comp3Incompleto = validarComparacion3Supermercados(itemsTestIncompleto);
        assertEq('3 Supermercados: Incompleto en Día % -> No comparable', comp3Incompleto.comparable, false);

        // Test 35: Comparación de 3 Supermercados (Presente en los 3 con misma presentación)
        var itemsTestCompleto = [
            { supermercado: 'Carrefour', valido: true, precio: 1500, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25 L' },
            { supermercado: 'COTO', valido: true, precio: 1550, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25 L' },
            { supermercado: 'Día %', valido: true, precio: 1480, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25 L' }
        ];
        var comp3Completo = validarComparacion3Supermercados(itemsTestCompleto);
        assertEq('3 Supermercados: Válido en los 3 -> Comparable', comp3Completo.comparable, true);

        // Test 36: Búsqueda por subcadenas (Obtener mayor cantidad de coincidencias posibles)
        var subsArroz = buscarPorSubcadenas('arroz');
        assertEq('Búsqueda por subcadenas: arroz encuentra al menos 2 productos', subsArroz.length >= 2, true);

        // Test 37: Búsqueda por subcadenas con candidatos
        var candTest = [
            'Fideos Tallarín Matarazzo 500g',
            'Fideos Tirabuzón Matarazzo 500g',
            'Arroz Gallo 1kg'
        ];
        var resCand = buscarPorSubcadenas('fideos matarazzo', candTest);
        assertEq('Búsqueda por subcadenas en lista: encuentra 2 de fideos', resCand.length, 2);

        // Test 38: Cálculo de subcadenas coincidentes
        var matchCalc = calcularCoincidenciasSubcadenas('Coca Cola 2.25L', 'Gaseosa Coca Cola Sabor Original 2.25 L');
        assertEq('Cálculo subcadenas coincidentes: cantidad > 0', matchCalc.cantidad > 0, true);

        console.log('----------------------------------------------------------------------');
        if (errores === 0) {
            console.log(' 🎉 DIAGNÓSTICO FINAL: TODAS LAS PRUEBAS DEL VALIDADOR PASARON CON ÉXITO\n');
            process.exit(0);
        } else {
            console.log(' ❌ DIAGNÓSTICO FINAL: SE DETECTARON ' + errores + ' ERRORES\n');
            process.exit(1);
        }
    } else if (args[0] === '--subcadenas' || args[0] === '--buscar') {
        var querySub = args.slice(1).join(' ').trim();
        var resSub = buscarPorSubcadenas(querySub);
        console.log('======================================================================');
        console.log('       🔍 RESULTADOS DE BÚSQUEDA POR SUBCADENAS (validador.js)');
        console.log('       Consulta: "' + querySub + '"');
        console.log('       Total de coincidencias obtenidas: ' + resSub.length);
        console.log('======================================================================\n');
        resSub.forEach(function(r, idx) {
            var nom = r.item ? r.item.nombre_completo : (r.texto || JSON.stringify(r.candidato));
            console.log((idx + 1) + '. ' + nom + ' [Score: ' + r.score + ' | Coincidencias: ' + r.cantidadCoincidencias + ']');
            console.log('   • Subcadenas coincidentes: ' + r.subcadenasCoincidentes.join(', '));
        });
    } else if (args[0] === '--cerrar-tagui') {
        cerrarNavegadorTagUI();
        console.log('[INFO] Navegador TagUI cerrado correctamente.');
    } else {
        console.log('Uso: node validador.js [--reporte-individual "producto"] | [--subcadenas "texto"] | [--limpiar 1|2|3] | [--crear-temp "producto"] | [--cerrar-tagui] | [--test|--diagnostico]');
    }
}

// Cierra exclusivamente las ventanas y procesos abiertos por TagUI (puerto 9222 y perfil tagui)
// de modo que NUNCA afecte al frontend (http://localhost:3000) ni al navegador personal del usuario.
function cerrarNavegadorTagUI() {
    try {
        const http = require('http');
        const req = http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const tabs = JSON.parse(data);
                    if (Array.isArray(tabs)) {
                        for (const tab of tabs) {
                            if (tab && tab.id) {
                                http.get(`http://127.0.0.1:9222/json/close/${tab.id}`, () => {}).on('error', () => {});
                            }
                        }
                    }
                } catch(e) {}
            });
        });
        req.on('error', () => {});
        req.setTimeout(800, () => req.destroy());
    } catch(e) {}

    try {
        const { spawnSync } = require('child_process');
        const res = spawnSync('powershell', [
            '-NoProfile',
            '-Command',
            "(Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%tagui%'\").ProcessId"
        ]);
        const pids = res.stdout.toString().split(/\r?\n/).map(s => s.trim()).filter(s => /^\d+$/.test(s));
        for (const pid of pids) {
            try {
                process.kill(parseInt(pid, 10), 'SIGKILL');
            } catch (eKill) {}
        }
    } catch (e) {}
}

// Adapta el separador decimal de cualquier número en el término de búsqueda según el supermercado.
// Detecta de forma genérica cualquier número decimal con punto (ej: 2.25, 1.5, 0.5)
// y, únicamente para Carrefour, convierte su separador a coma (2,25, 1,5, 0,5).
// Para COTO y Día %, mantiene el formato original con punto.
function adaptarTerminoSupermercado(termino, supermercado) {
    if (!termino || typeof termino !== 'string') return '';
    if (supermercado === 'Carrefour') {
        var res = termino.replace(/(\d+)\.(\d+)/g, function(match, entero, decimal) {
            return entero + ',' + decimal;
        });
        if (/coca\s*cola/i.test(res)) {
            res = res.replace(/(\d+,\d+)\s*(?:lts?|litros?|l)?\b/gi, function(m, num) {
                return num + ' lts';
            });
        }
        return res;
    }
    if (supermercado === 'Día %' || supermercado === 'Dia' || supermercado === 'Dia %' || (supermercado && String(supermercado).toLowerCase().includes('dia'))) {
        return termino.replace(/\blucchetti\b/gi, 'Luchetti');
    }
    return termino;
}

module.exports = {
    adaptarTerminoSupermercado: adaptarTerminoSupermercado,
    normalizar: normalizar,
    extraerSubcadenas: extraerSubcadenas,
    calcularCoincidenciasSubcadenas: calcularCoincidenciasSubcadenas,
    buscarPorSubcadenas: buscarPorSubcadenas,
    extraerPresentacion: extraerPresentacion,
    extraerAtributos: extraerAtributos,
    calcularPrecioNormalizado: calcularPrecioNormalizado,
    sonComparables: sonComparables,
    detectarIntencion: detectarIntencion,
    obtenerConfiguracionBusqueda: obtenerConfiguracionBusqueda,
    obtenerDiccionarioSupermercados: catalogo.obtenerDiccionarioSupermercados,
    buscarPorDiccionarioSupermercado: catalogo.buscarPorDiccionarioSupermercado,
    agregarNombreSupermercado: catalogo.agregarNombreSupermercado,
    validarCoincidencia: validarCoincidencia,
    validarComparacion3Supermercados: validarComparacion3Supermercados,
    catalogo: catalogo,
    parsePrecio: parsePrecio,
    formatoMoneda: formatoMoneda,
    leerResultadosCSV: leerResultadosCSV,
    mostrarReporteIndividual: mostrarReporteIndividual,
    limpiarResultados: limpiarResultados,
    crearTempInput: crearTempInput,
    cerrarNavegadorTagUI: cerrarNavegadorTagUI,
    MARCAS_CONOCIDAS: MARCAS_CONOCIDAS,
    DEFINICION_CATEGORIAS: DEFINICION_CATEGORIAS,
    CATEGORIAS_PRODUCTO: CATEGORIAS_PRODUCTO,
    ACCESORIOS_INCOMPATIBLES: ACCESORIOS_INCOMPATIBLES,
    SUBCATEGORIAS_COMUNES: SUBCATEGORIAS_COMUNES,
    LINEAS_PRODUCTO: LINEAS_PRODUCTO
};


