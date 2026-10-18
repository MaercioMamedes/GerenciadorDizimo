async function carregarParoquias(selectEl, idSelecionado) {
  if (selectEl.dataset.carregado === 'true') return;
  try {
    const resposta = await fetch('/paroquias/json');
    if (!resposta.ok) throw new Error('Falha ao buscar paróquias');
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
  const campoParoquia = document.getElementById('campo-paroquia');
  const selectParoquia = document.getElementById('paroquia_id');
  const campoTambemDizimista = document.getElementById('campo-tambem-dizimista');
  const dizimistaCheckbox = document.getElementById('tambem_dizimista');

  if (valor === 'administrador') {
    if (campoParoquia) {
      campoParoquia.style.display = 'block';
      selectParoquia.required = true;
      carregarParoquias(selectParoquia, selectParoquia.dataset.selecionado || '');
    }
    if (campoTambemDizimista) campoTambemDizimista.style.display = 'block';

    // Campos de dizimista só aparecem se o checkbox "também é dizimista" estiver marcado
    alternarCampoDizimista(dizimistaCheckbox ? dizimistaCheckbox.checked : false);
  } else {
    // Perfil Dizimista: oculta paróquia, oculta "também é dizimista" e limpa checkbox
    if (campoParoquia) {
      campoParoquia.style.display = 'none';
      selectParoquia.required = false;
      selectParoquia.value = '';
    }
    if (campoTambemDizimista) campoTambemDizimista.style.display = 'none';
    if (dizimistaCheckbox) dizimistaCheckbox.checked = false;

    // Dizimista SEMPRE exibe os campos de dizimista
    alternarCampoDizimista(true);
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
    // Admin cadastrando: executa uma única vez conforme o perfil selecionado
    alternarCampoParoquia(perfilSelect.value);

    perfilSelect.addEventListener('change', function () {
      alternarCampoParoquia(this.value);
    });

    const dizimistaCheckbox = document.getElementById('tambem_dizimista');
    if (dizimistaCheckbox) {
      dizimistaCheckbox.addEventListener('change', function () {
        alternarCampoDizimista(this.checked);
      });
    }
  } else {
    // Autocadastro público: sem select de perfil, sempre exibe campos de dizimista
    alternarCampoDizimista(true);
  }
});
