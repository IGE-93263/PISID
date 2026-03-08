use labirinto;

drop table if exists ocupacaolabirinto;
drop table if exists medicoespassagens;
drop table if exists mensagens;
drop table if exists temperatura;
drop table if exists som;
drop table if exists simulacao;
drop table if exists utilizador;
drop table if exists equipa;
drop table if exists sala;


create table equipa
(
   IDEquipa Integer not null,
   NomeEquipa varchar(100) null,

   constraint PK_equipa primary key (IDEquipa)
);


create table sala
(
   IDSala Integer not null,

   constraint PK_sala primary key (IDSala)
);


create table utilizador
(
   IDUtilizador Integer not null,
   Equipa Integer not null,
   Nome varchar(100) null,
   Telemovel varchar(20) null,
   Tipo varchar(50) null,
   Email varchar(120) null,
   DataNascimento date null,

   constraint PK_utilizador primary key (IDUtilizador)
);


create table simulacao
(
   IDSimulacao Integer not null,
   IDEquipa Integer not null,
   IDUtilizador Integer not null,
   Descricao text null,
   DataHoraInicio datetime null,

   constraint PK_simulacao primary key (IDSimulacao)
);


create table som
(
   IDSom Integer not null AUTO_INCREMENT,
   IDSimulacao Integer not null,
   Hora datetime null,
   Som varchar(50) null,

   constraint PK_som primary key (IDSom)
);


create table temperatura
(
   IDTemperatura Integer not null AUTO_INCREMENT,
   IDSimulacao Integer not null,
   Hora datetime null,
   Temperatura varchar(50) null,

   constraint PK_temperatura primary key (IDTemperatura)
);


create table mensagens
(
   IDMensagem Integer not null AUTO_INCREMENT,
   IDSimulacao Integer not null,
   IDSala Integer not null,
   Sensor varchar(100) null,
   Leitura decimal(10,2) null,
   TipoAlerta varchar(50) null,
   Msg varchar(255) null,
   HoraEscrita datetime null,
   Hora datetime null,

   constraint PK_mensagens primary key (IDMensagem)
);


create table medicoespassagens
(
   IDMedicao Integer not null AUTO_INCREMENT,
   IDSimulacao Integer not null,
   IDSalaOrigem Integer not null,
   IDSalaDestino Integer not null,
   Hora datetime null,
   Marsami Integer null,
   Status Integer null,

   constraint PK_medicoespassagens primary key (IDMedicao)
);


create table ocupacaolabirinto
(
   IDSimulacao Integer not null,
   IDSala Integer not null,
   DataCriacao timestamp not null,
   NumeroMarsamisEven Integer null,
   NumeroMarsamisOdd Integer null,

   constraint PK_ocupacaolabirinto primary key (IDSimulacao, IDSala, DataCriacao)
);



alter table utilizador
   add constraint FK_utilizador_equipa
   foreign key (Equipa)
   references equipa(IDEquipa)
   on delete restrict
   on update cascade
;


alter table simulacao
   add constraint FK_simulacao_equipa
   foreign key (IDEquipa)
   references equipa(IDEquipa)
   on delete restrict
   on update cascade
;


alter table simulacao
   add constraint FK_simulacao_utilizador
   foreign key (IDUtilizador)
   references utilizador(IDUtilizador)
   on delete restrict
   on update cascade
;


alter table som
   add constraint FK_som_simulacao
   foreign key (IDSimulacao)
   references simulacao(IDSimulacao)
   on delete cascade
   on update cascade
;


alter table temperatura
   add constraint FK_temperatura_simulacao
   foreign key (IDSimulacao)
   references simulacao(IDSimulacao)
   on delete cascade
   on update cascade
;


alter table mensagens
   add constraint FK_mensagens_simulacao
   foreign key (IDSimulacao)
   references simulacao(IDSimulacao)
   on delete cascade
   on update cascade
;


alter table mensagens
   add constraint FK_mensagens_sala
   foreign key (IDSala)
   references sala(IDSala)
   on delete restrict
   on update cascade
;


alter table medicoespassagens
   add constraint FK_medicoes_simulacao
   foreign key (IDSimulacao)
   references simulacao(IDSimulacao)
   on delete cascade
   on update cascade
;


alter table medicoespassagens
   add constraint FK_medicoes_sala_origem
   foreign key (IDSalaOrigem)
   references sala(IDSala)
   on delete restrict
   on update cascade
;


alter table medicoespassagens
   add constraint FK_medicoes_sala_destino
   foreign key (IDSalaDestino)
   references sala(IDSala)
   on delete restrict
   on update cascade
;


alter table ocupacaolabirinto
   add constraint FK_ocupacao_simulacao
   foreign key (IDSimulacao)
   references simulacao(IDSimulacao)
   on delete cascade
   on update cascade
;


alter table ocupacaolabirinto
   add constraint FK_ocupacao_sala
   foreign key (IDSala)
   references sala(IDSala)
   on delete restrict
   on update cascade
;