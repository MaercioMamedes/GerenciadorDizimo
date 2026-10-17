async function carregarParoquias(selectEl, idSelecionado) {
  if (selectEl.dataset.carregado === 'true') return;
  try {
    const resposta = await fetch('/paroquias/json', {
      credentials: 'include', // garante envio do cookie de sessão
    });
    if (!resposta.ok) throw new Error(`Falha ao buscar paróquias (status ${resposta.status})`);
    const paroquias = await resposta.json();
    selectEl.innerHTML = '<option value="">Selecione...</option>';
    paroquias.forEach(function (p) {
      const option = document.createElement('option');
      option.value = p.id;
      option.textContent = p.nome;
      if (idSelecionado && p.id === idSelecionado) option.selected = true;
      selectEl.appendChild(option);
    });
    selectEl.dataset.carregado = 'true';
  } catch (erro) {
    console.error('Erro ao carregar paróquias:', erro);
  }
}

function alternarCampoParoquia(valor) {
  const campo = document.getElementById('campo-paroquia');
  const select = document.getElementById('paroquia_id');
  const campoTambemDizimista = document.getElementById('campo-tambem-dizimista');
  const dizimistaCheckbox = document.getElementById('tambem_dizimista');

  if (valor === 'administrador') {
    campo.style.display = 'block';
    select.required = true;
    carregarParoquias(select, select.dataset.selecionado || '');

    if (campoTambemDizimista) campoTambemDizimista.style.display = 'block';
  } else {
    campo.style.display = 'none';
    select.required = false;
    select.value = '';

    // Perfil Dizimista já É dizimista: não faz sentido marcar "também é dizimista"
    if (campoTambemDizimista) campoTambemDizimista.style.display = 'none';
    if (dizimistaCheckbox && dizimistaCheckbox.checked) {
      dizimistaCheckbox.checked = false;
      alternarCampoDizimista(false);
    }
  }
}

function alternarCampoDizimista(marcado) {
  const campos = document.getElementById('campos-dizimista');
  if (!campos) return;

  const igrejaSelect = document.getElementById('igreja_id');

  if (marcado) {
    campos.style.display = 'block';
    if (igrejaSelect) igrejaSelect.required = true;
  } else {
    campos.style.display = 'none';
    if (igrejaSelect) {
      igrejaSelect.required = false;
      igrejaSelect.value = '';
    }
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const perfilSelect = document.getElementById('perfil');
  if (perfilSelect) {
    alternarCampoParoquia(perfilSelect.value);
  }

  const dizimistaCheckbox = document.getElementById('tambem_dizimista');
  if (dizimistaCheckbox) {
    alternarCampoDizimista(dizimistaCheckbox.checked);
  }
});
