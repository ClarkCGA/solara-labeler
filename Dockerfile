FROM jupyter/scipy-notebook:latest
RUN mamba install -c conda-forge leafmap geopandas "localtileserver>=0.10.0" osmnx -y && \
    pip install -U leafmap jsonschema==4.18.0 lonboard h5py xarray solara pydantic && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"
    
ENV PROJ_LIB='/opt/conda/share/proj'

USER root
RUN chown -R ${NB_UID} ${HOME}
USER ${NB_USER}

EXPOSE 8765
EXPOSE 8888

CMD ["solara", "run", "./solara-labeler/src/pages/", "--host=0.0.0.0"]
